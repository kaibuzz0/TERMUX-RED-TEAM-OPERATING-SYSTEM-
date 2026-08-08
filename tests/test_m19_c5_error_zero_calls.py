"""C5-ERROR: ERROR decision means adapter call count = 0.

When the Policy Engine returns DecisionState.ERROR (unknown actor, schema
violation, bounds failure, or internal exception), the broker's
validate_actions_for_policy() falls through to the generic PolicyError raise.
Broker.run() catches this in except Exception, returning denied with
execution_performed=False. dispatcher.run() is never reached.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hive_broker import Broker
from hive_broker.policy import validate_actions_for_policy


class TestErrorDecisionMeansZeroAdapterCalls:
    """ERROR decisions prevent adapter dispatch."""

    def _make_manifest(self):
        return {
            "schema_version": 1,
            "task_id": "test-error-task",
            "requestor": "test",
            "intent": "list-services",
            "required_capabilities": ["service.list"],
            "allowed_actions": ["service.list"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 10,
            "audit_level": "normal",
        }

    # ------------------------------------------------------------------
    # Structural: ERROR falls through to generic PolicyError
    # ------------------------------------------------------------------

    def test_validate_actions_catches_error_in_source(self):
        """validate_actions_for_policy source has fallback raise for ERROR."""
        src = inspect.getsource(validate_actions_for_policy)
        # The fallback after DENY/CONFIRM/DEFER checks
        assert "policy evaluation failed" in src, (
            "Fallback PolicyError must exist for ERROR and other states"
        )

    def test_error_follows_same_exception_path_as_deny(self):
        """ERROR, DENY, CONFIRM, DEFER all raise PolicyError caught by same path."""
        src = inspect.getsource(validate_actions_for_policy)
        # There are exactly 3 raise PolicyError statements:
        # 1. DENY branch
        # 2. CONFIRM/DEFER branch
        # 3. Fallback (catches ERROR and anything else)
        raises = src.count("raise PolicyError")
        assert raises == 3, (
            f"Expected 3 PolicyError raises, found {raises}"
        )

    # ------------------------------------------------------------------
    # Behavioral: ERROR mocked → 0 dispatcher calls
    # ------------------------------------------------------------------

    def test_error_decision_does_not_call_dispatcher(self):
        """Monkeypatched ERROR decision → 0 dispatcher calls."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run

        import hive_broker.policy as policy_module
        original_validate = policy_module.validate_actions_for_policy
        def fake_error(actions, policy, context):
            from hive_broker.errors import PolicyError
            raise PolicyError("Simulated ERROR: policy evaluation failed")
        policy_module.validate_actions_for_policy = fake_error
        try:
            manifest = self._make_manifest()
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert result["execution_performed"] is False
            assert call_count[0] == 0, (
                f"Dispatcher called {call_count[0]} times on ERROR"
            )
        finally:
            policy_module.validate_actions_for_policy = original_validate
            broker.dispatcher.run = original_run

    def test_error_response_contains_policy_decision_deny(self):
        """ERROR produces 'denied' response with policy_decision=DENY in except block."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        import hive_broker.policy as policy_module
        original_validate = policy_module.validate_actions_for_policy
        def fake_error(actions, policy, context):
            from hive_broker.errors import PolicyError
            raise PolicyError("Simulated ERROR")
        policy_module.validate_actions_for_policy = fake_error
        try:
            manifest = self._make_manifest()
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert result["policy_decision"] == "DENY"
            assert result["execution_performed"] is False
        finally:
            policy_module.validate_actions_for_policy = original_validate

    # ------------------------------------------------------------------
    # DecisionState.ALLOW is the only path to dispatcher
    # ------------------------------------------------------------------

    def test_allow_is_only_state_that_does_not_raise(self):
        """Source inspection: only ALLOW bypasses the raise statements."""
        src = inspect.getsource(validate_actions_for_policy)
        # The condition is: if decision.decision not in (DecisionState.ALLOW,)
        assert "DecisionState.ALLOW" in src
        assert "not in" in src or "!= DecisionState.ALLOW" in src, (
            "ALLOW must be the exclusive bypass condition"
        )
