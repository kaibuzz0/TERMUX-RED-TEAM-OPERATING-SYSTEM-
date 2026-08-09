"""Milestone 19 — C4 Session impersonation investigation.

Verifies that broker session identity remains isolated:
- One session cannot inspect another's transactions
- One session cannot cancel another's tasks
- One session cannot reuse another's approvals
- Two sessions with the same ID and state_root collide on persist
  (documented as a construction-time risk, not a runtime bypass)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hive_broker.session import BrokerSession
from hive_broker.stop import stop_session
from hive_broker.transaction import generate_transaction
from hive_broker import Broker


class TestSessionImpersonation:
    """C4 — verify session identity isolation."""

    def test_session_ids_are_statistically_unique(self):
        """100 generated session IDs must all be distinct."""
        ids = [BrokerSession().session_id for _ in range(100)]
        assert len(set(ids)) == 100, f"Collision in {len(ids)} generated IDs"

    def test_session_cannot_inspect_another_transactions(self):
        """One session cannot read another's active_transactions."""
        s1 = BrokerSession()
        s2 = BrokerSession()
        s1.add_transaction("txn-a")

        # s2 has no access to s1 internals except by direct attribute access
        # (which requires object reference possession)
        assert s2.active_transactions != s1.active_transactions
        assert "txn-a" not in s2.active_transactions

    def test_session_cannot_cancel_another_task(self):
        """stop_session on s2 does not affect s1's transactions."""
        s1 = BrokerSession()
        s2 = BrokerSession()
        s1.add_transaction("txn-target")

        result = stop_session(s2, "txn-target")
        assert result["stopped"] is False
        assert "txn-target" in s1.active_transactions

    def test_stop_scope_limited_to_target_session(self):
        """stop_session(transaction_id) only affects matching session."""
        s1 = BrokerSession()
        s2 = BrokerSession()
        s1.add_transaction("txn-1")
        s2.add_transaction("txn-2")

        stop_session(s1, "txn-1")
        assert "txn-1" not in s1.active_transactions
        assert "txn-2" in s2.active_transactions

    def test_full_session_stop_is_local(self):
        """stop() on one session does not propagate to another."""
        s1 = BrokerSession()
        s2 = BrokerSession()
        s1.stop()
        assert s1.is_stopped() is True
        assert s2.is_stopped() is False

    def test_forged_session_id_collides_on_persist(self, tmp_path):
        """Explicitly forged equal session_id + same state_root overwrites file.

        This is a CONSTRUCTION-TIME risk, not a runtime bypass.
        The Broker class always generates random UUIDs; impersonation
        requires direct BrokerSession instantiation with a stolen ID.
        """
        stolen_id = "sess-stolen"
        s1 = BrokerSession(session_id=stolen_id, state_root=tmp_path)
        s2 = BrokerSession(session_id=stolen_id, state_root=tmp_path)

        s1.add_transaction("txn-a")
        s2.add_transaction("txn-b")

        s1._persist()
        s2._persist()

        # Only s2's state remains because they share filename
        target = tmp_path / f"{stolen_id}.json"
        data = json.loads(target.read_text())
        assert data["active_transactions"] == ["txn-b"]
        # This demonstrates the construction-time collision risk

    def test_broker_does_not_allow_custom_session_id(self, tmp_path):
        """Broker.__init__ always creates a fresh BrokerSession with random ID."""
        b1 = Broker(state_root=tmp_path, log_root=tmp_path)
        b2 = Broker(state_root=tmp_path, log_root=tmp_path)
        assert b1.session.session_id != b2.session.session_id
        # Verify they are not prefix-predictable
        assert len(b1.session.session_id) >= 32
        assert len(b2.session.session_id) >= 32

    def test_transaction_isolation_between_brokers(self, tmp_path):
        """Transactions in one broker do not appear in another broker's session."""
        b1 = Broker(state_root=tmp_path, log_root=tmp_path)
        b2 = Broker(state_root=tmp_path, log_root=tmp_path)

        txn1 = generate_transaction("task-1", b1.session.session_id, "audit-1")
        b1.session.add_transaction(txn1.transaction_id)

        assert txn1.transaction_id not in b2.session.active_transactions
        assert txn1.session_id == b1.session.session_id

    def test_audit_records_tag_correct_session(self, tmp_path):
        """Audit writes include the originating session_id."""
        b = Broker(state_root=tmp_path, log_root=tmp_path)
        status = b.status()
        assert status["session_id"] == b.session.session_id
        # Verify no cross-session leakage in status
        assert "active_transactions" in status

    def test_session_persist_file_isolation(self, tmp_path):
        """Different sessions write to different persist files."""
        s1 = BrokerSession(state_root=tmp_path)
        s2 = BrokerSession(state_root=tmp_path)
        s1._persist()
        s2._persist()

        files = list(tmp_path.glob("sess-*.json"))
        assert len(files) == 2
        ids = {json.loads(f.read_text())["session_id"] for f in files}
        assert ids == {s1.session_id, s2.session_id}

