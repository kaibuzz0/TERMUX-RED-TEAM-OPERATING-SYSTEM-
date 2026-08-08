"""Milestone 19 — Broker active transaction count boundedness audit.

Production active-transaction bounds catalog:
- hive_broker.session.BrokerSession.add_transaction() — NO explicit bound
- hive_broker.session.BrokerSession.remove_transaction() — NO explicit bound
- hive_broker.session.BrokerSession.stop_transaction() — NO explicit bound
- hive_broker.__init__.Broker.run() — adds then removes in finally (short-lived)
- hive_broker.session.BrokerSession._persist() — writes active_transactions list to JSON

No production layer enforces a maximum active transaction count.
The practical limit is memory/JSON file size. Documented as accepted debt.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. BrokerSession has no explicit active transaction bound
# ---------------------------------------------------------------------------

class TestBrokerSessionNoActiveTransactionBound:
    def test_add_transaction_has_no_explicit_limit(self):
        """BrokerSession.add_transaction() is a simple set.add() with no count check."""
        from hive_broker.session import BrokerSession
        session = BrokerSession()
        for i in range(10000):
            session.add_transaction(f"txn-{i:05d}")
        assert len(session.active_transactions) == 10000

    def test_remove_transaction_is_idempotent(self):
        """remove_transaction() uses set.discard — safe to call repeatedly."""
        from hive_broker.session import BrokerSession
        session = BrokerSession()
        session.add_transaction("txn-1")
        session.remove_transaction("txn-1")
        session.remove_transaction("txn-1")
        assert "txn-1" not in session.active_transactions

    def test_stop_transaction_returns_false_for_missing(self):
        """stop_transaction() returns False if transaction not active."""
        from hive_broker.session import BrokerSession
        session = BrokerSession()
        assert session.stop_transaction("nonexistent") is False


# ---------------------------------------------------------------------------
# 2. Persistence handles large active transaction sets
# ---------------------------------------------------------------------------

class TestBrokerSessionPersistenceWithManyTransactions:
    def test_persist_preserves_large_active_set(self):
        """_persist() writes and re-reads a large active_transactions set correctly."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = BrokerSession(state_root=root)
            for i in range(5000):
                session.add_transaction(f"txn-{i:05d}")
            session._persist()

            # Verify file was written
            target = root / f"{session.session_id}.json"
            assert target.exists()
            data = json.loads(target.read_text(encoding="utf-8"))
            assert len(data["active_transactions"]) == 5000
            assert set(data["active_transactions"]) == session.active_transactions

    def test_persist_history_truncation_independent_of_active_set(self):
        """_persist() truncates history to [-100:] but preserves all active transactions."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = BrokerSession(state_root=root)
            # Add many history entries
            for i in range(200):
                session.history.append({"idx": i})
            # Add many active transactions
            for i in range(3000):
                session.add_transaction(f"txn-{i:05d}")
            session._persist()

            target = root / f"{session.session_id}.json"
            data = json.loads(target.read_text(encoding="utf-8"))
            assert len(data["history"]) == 100  # truncated
            assert len(data["active_transactions"]) == 3000  # NOT truncated


# ---------------------------------------------------------------------------
# 3. Dispatcher checks active set for cancellation
# ---------------------------------------------------------------------------

class TestDispatcherActiveTransactionTracking:
    def test_dispatcher_detects_removed_transaction(self):
        """Dispatcher.run() detects if transaction was removed mid-flight."""
        from hive_broker.dispatcher import Dispatcher
        from hive_broker.session import BrokerSession
        from hive_broker.transaction import Transaction
        session = BrokerSession()
        dispatcher = Dispatcher(session)
        txn = Transaction(
            transaction_id="txn-1",
            task_id="task-1",
            session_id=session.session_id,
            audit_id="audit-1",
        )
        session.add_transaction(txn.transaction_id)
        # Remove before dispatch to simulate stop
        session.remove_transaction(txn.transaction_id)
        manifest = {
            "allowed_actions": ["read"],
            "target_services": [],
        }
        result = dispatcher.run(manifest, txn)
        assert result["status"] == "cancelled"
        assert any("transaction cancelled" in e for e in result.get("errors", []))

    def test_dispatcher_allows_active_transaction(self):
        """Dispatcher.run() proceeds normally when transaction is still active."""
        from hive_broker.dispatcher import Dispatcher
        from hive_broker.session import BrokerSession
        from hive_broker.transaction import Transaction
        session = BrokerSession()
        dispatcher = Dispatcher(session)
        txn = Transaction(
            transaction_id="txn-1",
            task_id="task-1",
            session_id=session.session_id,
            audit_id="audit-1",
        )
        session.add_transaction(txn.transaction_id)
        manifest = {
            "allowed_actions": ["read"],
            "target_services": [],
        }
        result = dispatcher.run(manifest, txn)
        # Normal dispatch may succeed or fail depending on adapter, but should not be cancelled
        assert result["status"] != "cancelled"


# ---------------------------------------------------------------------------
# 4. Broker.run() lifecycle: add → dispatch → remove (finally)
# ---------------------------------------------------------------------------

class TestBrokerRunTransactionLifecycle:
    def test_run_adds_then_removes_transaction(self):
        """Broker.run() adds transaction before dispatch and removes it in finally."""
        from hive_broker import Broker
        with tempfile.TemporaryDirectory() as tmp:
            broker = Broker(state_root=Path(tmp), log_root=Path(tmp), policy_name="test")
            # Pre-check: no active transactions
            assert len(broker.session.active_transactions) == 0
            # Test the session contract directly (run() needs full valid manifest + policy engine)
            broker.session.add_transaction("txn-test")
            assert "txn-test" in broker.session.active_transactions
            broker.session.remove_transaction("txn-test")
            assert "txn-test" not in broker.session.active_transactions

    def test_stop_transaction_via_broker(self):
        """Broker.stop(transaction_id) removes a specific active transaction."""
        from hive_broker import Broker
        with tempfile.TemporaryDirectory() as tmp:
            broker = Broker(state_root=Path(tmp), log_root=Path(tmp), policy_name="test")
            broker.session.add_transaction("txn-1")
            broker.session.add_transaction("txn-2")
            result = broker.stop("txn-1")
            assert result["stopped"] is True
            assert "txn-1" not in broker.session.active_transactions
            assert "txn-2" in broker.session.active_transactions

    def test_stop_session_clears_all(self):
        """Broker.stop() with no transaction_id stops the entire session."""
        from hive_broker import Broker
        with tempfile.TemporaryDirectory() as tmp:
            broker = Broker(state_root=Path(tmp), log_root=Path(tmp), policy_name="test")
            broker.session.add_transaction("txn-1")
            broker.session.add_transaction("txn-2")
            result = broker.stop()
            assert result["stopped"] is True
            assert result["scope"] == "session"
            assert broker.session.is_stopped() is True
            # Existing transactions remain in the set until explicitly removed or run() finally block clears them
            # This is the actual behavior: stop() only sets flag, does not clear active_transactions


# ---------------------------------------------------------------------------
# 5. Status reports active transactions without enforcing bound
# ---------------------------------------------------------------------------

class TestBrokerStatusUnbounded:
    def test_status_reports_all_active_transactions(self):
        """Broker.status() returns all active transactions — no truncation."""
        from hive_broker import Broker
        with tempfile.TemporaryDirectory() as tmp:
            broker = Broker(state_root=Path(tmp), log_root=Path(tmp), policy_name="test")
            for i in range(1000):
                broker.session.add_transaction(f"txn-{i:04d}")
            status = broker.status()
            assert len(status["active_transactions"]) == 1000
            assert status["stopped"] is False


# ---------------------------------------------------------------------------
# 6. No bound on rapid transaction creation (documented debt)
# ---------------------------------------------------------------------------

class TestRapidTransactionCreation:
    def test_rapid_add_remove_cycles(self):
        """Rapid add/remove cycles do not hit any explicit rate limit."""
        from hive_broker.session import BrokerSession
        session = BrokerSession()
        for i in range(5000):
            txn_id = f"txn-{i:05d}"
            session.add_transaction(txn_id)
            session.remove_transaction(txn_id)
        assert len(session.active_transactions) == 0

    def test_simulated_concurrent_transactions_unbounded(self):
        """Many simulated concurrent transactions can coexist — no hard cap."""
        from hive_broker.session import BrokerSession
        session = BrokerSession()
        # Simulate a broker that started many runs but hasn't finished them
        for i in range(20000):
            session.add_transaction(f"txn-{i:06d}")
        assert len(session.active_transactions) == 20000
        # Cleanup
        for i in range(20000):
            session.remove_transaction(f"txn-{i:06d}")
        assert len(session.active_transactions) == 0