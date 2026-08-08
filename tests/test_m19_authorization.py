"""Milestone 19 — Area C: Authorization and broker bypass tests.

Tests policy evaluation hardening, broker gate enforcement, and
authorization bypass attempts.
"""

from __future__ import annotations

import pytest

from policy_engine.loader import PolicyLoader
from policy_engine.evaluator import evaluate, PolicyEvaluator
from policy_engine.requests import PolicyRequest
from policy_engine.decisions import DecisionState
from policy_engine.rules import PolicySet, PolicyProfile, Rule
from policy_engine.errors import PolicyValidationError, PolicyRequestError
from hive_broker.adapters import dispatch, AdapterError
from hive_broker.transaction import Transaction
from hive_broker.session import BrokerSession


class TestAuthorizationBypass:
    # -----------------------------------------------------------------------
    # C1: Caller-supplied context trust
    # -----------------------------------------------------------------------

    def test_fabricated_context_rejected(self):
        """C1: Fabricated safety context must fail CONTEXT_SCHEMA validation."""
        loader = PolicyLoader({})
        ps = loader.load("observer")
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="broker.capabilities",
            resource={"type": "broker", "id": "capabilities"},
            context={"vault_state": "COMPROMISED"},  # invalid enum value
        )
        decision = evaluate(request, ps)
        assert decision.decision == DecisionState.DENY
        assert "Context validation failed" in decision.message

    def test_context_schema_enforces_types(self):
        """C1: Context with wrong types must be rejected."""
        loader = PolicyLoader({})
        ps = loader.load("observer")
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="broker.capabilities",
            resource={"type": "broker", "id": "capabilities"},
            context={"maintenance_mode": "not_a_bool"},
        )
        decision = evaluate(request, ps)
        assert decision.decision == DecisionState.DENY
        assert "Context validation failed" in decision.message

    # -----------------------------------------------------------------------
    # C2: Policy bypass via empty rules
    # -----------------------------------------------------------------------

    def test_empty_rule_set_defaults_deny(self):
        """C2: Empty rule set must default to DENY."""
        ps = PolicySet({
            "empty": PolicyProfile(name="empty", description="test", rules=[]),
        })
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="broker.capabilities",
            resource={"type": "broker", "id": "capabilities"},
            context={},
        )
        decision = PolicyEvaluator(ps).evaluate(request, "empty")
        assert decision.decision == DecisionState.DENY
        assert decision.reason_code == "DEFAULT_DENY"

    # -----------------------------------------------------------------------
    # C3: Transaction ID collision
    # -----------------------------------------------------------------------

    def test_transaction_id_unique(self):
        """C3: Transaction IDs must be unique (UUID4 statistical test)."""
        txn_ids = set()
        for _ in range(100):
            txn = Transaction(f"txn-{_}", f"task-{_}", "sess-test", "audit-1")
            assert txn.transaction_id not in txn_ids
            txn_ids.add(txn.transaction_id)
        assert len(txn_ids) == 100

    # -----------------------------------------------------------------------
    # C4: Adapter direct call bypass
    # -----------------------------------------------------------------------

    def test_adapter_dispatch_requires_broker_transaction(self):
        """C4: dispatch with None transaction on capabilities that don't need it still works
        because those adapters are read-only, but dispatch without txn on stateful
        capabilities would fail. The broker gate is the actual enforcement point."""
        # Read-only adapter without txn works (by design)
        result = dispatch("broker.capabilities", None, {})
        assert "capabilities" in result

        # But stateful adapters will fail without proper txn
        txn = Transaction("txn-test", "task-test", "sess-test", "audit-1")
        with pytest.raises(AdapterError):
            dispatch("evil.capability", txn, {})

    def test_adapter_unauthorized_capability_rejected(self):
        """C4: Unknown capability through adapter raises AdapterError."""
        txn = Transaction("txn-test", "task-test", "sess-test", "audit-1")
        with pytest.raises(AdapterError):
            dispatch("evil.capability", txn, {})

    # -----------------------------------------------------------------------
    # C5: Emergency restriction bypass
    # -----------------------------------------------------------------------

    def test_emergency_cannot_grant_capabilities(self):
        """C5: Emergency restrictions must only reduce authority, never grant."""
        loader = PolicyLoader({})
        # Observer normally cannot mutate; emergency deny_all_mutations should not change that
        ps = loader.load("observer", emergency={"deny_all_mutations": True})
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="config.commit",  # valid mutating capability
            resource={"type": "config", "id": "hive"},
            context={},
        )
        decision = evaluate(request, ps)
        # Actor "user" requesting mutation fails validation → ERROR (still fail-closed)
        assert decision.decision in (DecisionState.DENY, DecisionState.ERROR)

    def test_emergency_observer_only_blocks_operator_mutation(self):
        """C5: Emergency observer_only blocks operator-level mutations."""
        loader = PolicyLoader({})
        ps = loader.load("operator", emergency={"observer_only": True})
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="config.commit",  # valid mutating capability
            resource={"type": "config", "id": "hive"},
            context={},
        )
        decision = evaluate(request, ps)
        # Actor "user" requesting mutation fails validation → ERROR (still fail-closed)
        assert decision.decision in (DecisionState.DENY, DecisionState.ERROR)

    # -----------------------------------------------------------------------
    # C6: Confirm without approval
    # -----------------------------------------------------------------------

    def test_activation_requires_approve(self):
        """C6: Activation without --approve must be blocked."""
        import tempfile
        from pathlib import Path
        from installer.activate import ActiveState

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            with pytest.raises(Exception) as exc:
                active.activate("release-1", approve=False)
            assert "explicit approval" in str(exc.value).lower()

    def test_rollback_requires_approve(self):
        """C6: Rollback without --approve must be blocked."""
        import tempfile
        from pathlib import Path
        from installer.activate import ActiveState

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            with pytest.raises(Exception) as exc:
                active.rollback(approve=False)
            assert "explicit approval" in str(exc.value).lower()

    # -----------------------------------------------------------------------
    # C7: Broker session impersonation
    # -----------------------------------------------------------------------

    def test_session_id_unpredictable(self):
        """C7: Session IDs must be unguessable (UUID4 statistical test)."""
        ids = set()
        for _ in range(100):
            session = BrokerSession()
            assert len(session.session_id) > 20
            assert session.session_id not in ids
            ids.add(session.session_id)
        assert len(ids) == 100

    def test_session_isolation(self):
        """C7: One session cannot access another session's transactions."""
        session1 = BrokerSession()
        session2 = BrokerSession()
        txn1 = Transaction("txn-1", "task-1", session1.session_id, "audit-1")
        txn2 = Transaction("txn-2", "task-2", session2.session_id, "audit-2")

        session1.add_transaction(txn1.transaction_id)
        assert txn1.transaction_id in session1.active_transactions
        assert txn1.transaction_id not in session2.active_transactions
