"""C5-POLICY-DENY: Policy DENY means adapter call count = 0.

The Broker.run() method validates policy BEFORE calling dispatcher.run().
If policy validation raises, the except block returns a "denied" response with
execution_performed=False — dispatcher.run() is never reached.

This test verifies that structural property both by code inspection and by
behavioral proof with a mock.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hive_broker import Broker
from hive_broker.schema import validate_manifest


class TestPolicyDenyMeansZeroAdapterCalls:
    """Policy DENY prevents any adapter dispatch."""

    def _make_manifest(self, intent="list-services", actions=None, read_only=True):
        return {
            "schema_version": 1,
            "task_id": "test-deny-task",
            "requestor": "test",
            "intent": intent,
            "required_capabilities": actions or ["service.list"],
            "allowed_actions": actions or ["service.list"],
            "target_services": [],
            "target_paths": [],
            "read_only": read_only,
            "timeout_seconds": 10,
            "audit_level": "normal",
        }

    # ------------------------------------------------------------------
    # Structural: dispatcher.run() is after policy gate, inside try block
    # ------------------------------------------------------------------

    def test_broker_run_structure_policy_before_dispatcher(self):
        """Broker.run source: validate_actions_for_policy precedes dispatcher.run()."""
        src = inspect.getsource(Broker.run)
        policy_idx = src.find("validate_actions_for_policy")
        dispatcher_idx = src.find("self.dispatcher.run")
        assert policy_idx != -1, "validate_actions_for_policy not found"
        assert dispatcher_idx != -1, "self.dispatcher.run not found"
        assert policy_idx < dispatcher_idx, (
            "Policy gate must precede dispatcher.run()"
        )

    def test_broker_run_structure_dispatcher_in_try_after_policy(self):
        """self.dispatcher.run() is inside the second try block (after policy except)."""
        src = inspect.getsource(Broker.run)
        # There are two try blocks: first for policy, second for dispatcher
        first_try = src.find("try:")
        first_except = src.find("except Exception as e:")
        second_try = src.find("try:", first_try + 1)
        dispatcher_idx = src.find("self.dispatcher.run")
        second_except = src.find("except BrokerError", second_try)
        assert first_try < first_except < second_try < dispatcher_idx < second_except, (
            "dispatcher.run() must be in second try block after policy except"
        )

    def test_broker_run_returns_denied_on_policy_failure(self):
        """Policy failure returns status='denied' with execution_performed=False."""
        src = inspect.getsource(Broker.run)
        except_start = src.find("except Exception as e:")
        except_section = src[except_start:except_start + 800]
        assert '"status": "denied"' in except_section, (
            "Except block must return denied status"
        )
        assert '"execution_performed": False' in except_section, (
            "Except block must set execution_performed=False"
        )

    def test_broker_run_no_dispatcher_in_except_block(self):
        """The except Exception block contains no dispatcher.run() call."""
        src = inspect.getsource(Broker.run)
        except_start = src.find("except Exception as e:")
        # Find the next try or method boundary
        next_block = src.find("try:", except_start + 1)
        if next_block == -1:
            next_block = len(src)
        except_section = src[except_start:next_block]
        assert "self.dispatcher.run" not in except_section, (
            "Dispatcher must not be called in except block"
        )

    # ------------------------------------------------------------------
    # Behavioral: mock proves 0 adapter calls on policy DENY
    # ------------------------------------------------------------------

    def test_policy_deny_returns_execution_performed_false(self):
        """Policy evaluation failure returns denied with execution_performed=False."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        # Monkeypatch validate_actions_for_policy to always deny
        import hive_broker.policy as policy_module
        original = policy_module.validate_actions_for_policy
        def fake_deny(actions, policy, context):
            raise Exception("Simulated policy denial")
        policy_module.validate_actions_for_policy = fake_deny
        try:
            manifest = self._make_manifest(intent="list-services", actions=["service.list"], read_only=True)
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert result["execution_performed"] is False
            assert "policy" in str(result.get("errors", [])).lower()
        finally:
            policy_module.validate_actions_for_policy = original

    def test_policy_deny_does_not_call_dispatcher(self):
        """Policy DENY never calls dispatcher.run() — call count remains 0."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        # Track dispatcher calls
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run

        import hive_broker.policy as policy_module
        original_validate = policy_module.validate_actions_for_policy
        def fake_deny(actions, policy, context):
            raise Exception("Simulated policy denial")
        policy_module.validate_actions_for_policy = fake_deny
        try:
            manifest = self._make_manifest(intent="list-services", actions=["service.list"], read_only=True)
            result = broker.run(manifest)
            assert result["status"] == "denied"
            assert call_count[0] == 0, (
                f"Dispatcher called {call_count[0]} times on policy DENY"
            )
        finally:
            policy_module.validate_actions_for_policy = original_validate
            broker.dispatcher.run = original_run

    def test_policy_allow_calls_dispatcher(self):
        """Policy ALLOW calls dispatcher.run() — call count = 1."""
        broker = Broker(Path("/tmp"), Path("/tmp"), policy_name="observer")
        original_run = broker.dispatcher.run
        call_count = [0]
        def counting_run(manifest, txn):
            call_count[0] += 1
            return original_run(manifest, txn)
        broker.dispatcher.run = counting_run

        # service.list is read-only and allowed by observer
        manifest = self._make_manifest(intent="list-services", actions=["service.list"], read_only=True)
        result = broker.run(manifest)
        assert result["status"] == "success"
        assert call_count[0] == 1, (
            f"Dispatcher called {call_count[0]} times on policy ALLOW"
        )
        broker.dispatcher.run = original_run

    # ------------------------------------------------------------------
    # validate_actions_for_policy gate is explicit
    # ------------------------------------------------------------------

    def test_policy_gate_imported_in_run_method(self):
        """validate_actions_for_policy is imported inside Broker.run, not at module level."""
        src = inspect.getsource(Broker.run)
        assert "from hive_broker.policy import validate_actions_for_policy" in src

    def test_except_block_returns_structured_denied(self):
        """The except block returns a structured dict with all required fields."""
        src = inspect.getsource(Broker.run)
        except_start = src.find("except Exception as e:")
        next_block = src.find("try:", except_start + 1)
        if next_block == -1:
            next_block = len(src)
        except_section = src[except_start:next_block]
        required_fields = [
            "schema_version", "transaction_id", "task_id", "session_id",
            "audit_id", "intent", "status", "results", "errors",
            "duration_ms", "policy_decision", "execution_performed",
        ]
        for field in required_fields:
            assert f'"{field}"' in except_section or f"'{field}'" in except_section, (
                f"Required field {field} missing from denied response"
            )
