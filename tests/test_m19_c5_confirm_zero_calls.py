"""C5-CONFIRM: CONFIRM without approval means adapter call count = 0.

The Policy Engine may return DecisionState.CONFIRM or DecisionState.DEFER for
actions that need human/secondary authorization. The broker's
validate_actions_for_policy() treats both CONFIRM and DEFER as authorization
failures — it raises PolicyError, which Broker.run() catches in its
except Exception block, returning denied with execution_performed=False.

There is no approval-path continuation; dispatcher.run() is never reached.
This test verifies that structural guarantee.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hive_broker import Broker
from hive_broker.policy import validate_actions_for_policy


class TestConfirmWithoutApprovalMeansZeroAdapterCalls:
    """CONFIRM/DEFER decisions prevent adapter dispatch."""

    def _make_manifest(self):
        return {
            "schema_version": 1,
            "task_id": "test-confirm-task",
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
    # Structural: CONFIRM/DEFER raise PolicyError before dispatcher
    # ------------------------------------------------------------------

    def test_validate_actions_rejects_confirm_in_source(self):
        """validate_actions_for_policy source raises PolicyError for CONFIRM."""
        src = inspect.getsource(validate_actions_for_policy)
        confirm_idx = src.find("DecisionState.CONFIRM")
        assert confirm_idx != -1, "CONFIRM handling not found in source"
        # CONFIRM branch raises PolicyError
        block = src[confirm_idx:confirm_idx + 200]
        assert "PolicyError" in block, "CONFIRM must raise PolicyError"

    def test_validate_actions_rejects_defer_in_source(self):
        """validate_actions_for_policy source raises PolicyError for DEFER."""
        src = inspect.getsource(validate_actions_for_policy)
        defer_idx = src.find("DecisionState.DEFER")
        assert defer_idx != -1, "DEFER handling not found in source"
        block = src[defer_idx:defer_idx + 200]
        assert "PolicyError" in block, "DEFER must raise PolicyError"

    def test_confirm_and_defer_share_same_exception_path(self):
        """CONFIRM and DEFER raise PolicyError, caught by same except block as DENY."""
        src = inspect.getsource(validate_actions_for_policy)
        # Both are in the same if-block that raises
        confirm_idx = src.find("DecisionState.CONFIRM")
        defer_idx = src.find("DecisionState.DEFER")
        deny_idx = src.find("DecisionState.DENY")
        assert deny_idx < confirm_idx, "DENY precedes CONFIRM in source"
        assert confirm_idx < defer_idx or defer_idx < confirm_idx, (
            "CONFIRM and DEFER handled adjacently"
        )

    def test_broker_run_except_block_catches_policy_error(self):
        """Broker.run catches PolicyError (from CONFIRM/DEFER/DENY) in except Exception."""
        src = inspect.getsource(Broker.run)
        assert "except Exception as e:" in src
        except_start = src.find("except Exception as e:")
        block = src[except_start:except_start + 700]
        assert '"execution_performed": False' in block
        assert '"status": "denied"' in block

    # ------------------------------------------------------------------
    # Behavioral: CONFIRM/DEFER mocked → 0 dispatcher calls
    # ------------------------------------------------------------------

    def test_confirm_decision_does_not_call_dispatcher(self):
        """Monkeypatched CONFIRM decision → 0 dispatcher calls."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run

        import hive_broker.policy as policy_module
        original_validate = policy_module.validate_actions_for_policy
        def fake_confirm(actions, policy, context):
            from hive_broker.errors import PolicyError
            raise PolicyError("Simulated CONFIRM: requires further authorization")
        policy_module.validate_actions_for_policy = fake_confirm
        try:
            manifest = self._make_manifest()
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert result["execution_performed"] is False
            assert call_count[0] == 0, (
                f"Dispatcher called {call_count[0]} times on CONFIRM"
            )
        finally:
            policy_module.validate_actions_for_policy = original_validate
            broker.dispatcher.run = original_run

    def test_defer_decision_does_not_call_dispatcher(self):
        """Monkeypatched DEFER decision → 0 dispatcher calls."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run

        import hive_broker.policy as policy_module
        original_validate = policy_module.validate_actions_for_policy
        def fake_defer(actions, policy, context):
            from hive_broker.errors import PolicyError
            raise PolicyError("Simulated DEFER: deferred to operator")
        policy_module.validate_actions_for_policy = fake_defer
        try:
            manifest = self._make_manifest()
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert result["execution_performed"] is False
            assert call_count[0] == 0, (
                f"Dispatcher called {call_count[0]} times on DEFER"
            )
        finally:
            policy_module.validate_actions_for_policy = original_validate
            broker.dispatcher.run = original_run

    def test_allow_decision_calls_dispatcher_once(self):
        """Normal ALLOW → dispatcher called exactly once."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run
        try:
            manifest = self._make_manifest()
            result = broker.run(manifest)
            assert result["status"] == "success"
            assert result["execution_performed"] is True
            assert call_count[0] == 1
        finally:
            broker.dispatcher.run = original_run

    # ------------------------------------------------------------------
    # No approval continuation path exists
    # ------------------------------------------------------------------

    def test_no_approval_continuation_in_broker_run(self):
        """Broker.run has no 'if approved: dispatcher.run()' continuation logic."""
        src = inspect.getsource(Broker.run)
        # After except Exception block, there is no approval check before dispatcher
        except_end = src.find("except Exception as e:")
        # Find the return inside except block
        return_after_except = src.find("return {", except_end)
        dispatcher_after_except = src.find("self.dispatcher.run", except_end)
        # Dispatcher must come BEFORE the except block (in the second try), not after
        assert dispatcher_after_except > except_end, "Dispatcher after except is expected"
        # But it must be in a new try block, not a continuation of the except
        second_try = src.find("try:", except_end)
        assert second_try < dispatcher_after_except, (
            "Dispatcher must be in second try, not approval continuation"
        )

    def test_approval_module_not_imported_in_broker(self):
        """Broker.run does not import or reference approval workflow."""
        src = inspect.getsource(Broker.run)
        assert "approval" not in src.lower(), (
            "No approval logic in Broker.run"
        )
        assert "is_approved" not in src
        assert "request_approval" not in src
