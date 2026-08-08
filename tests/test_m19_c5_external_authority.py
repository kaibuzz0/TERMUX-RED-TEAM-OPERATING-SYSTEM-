"""C5: External authority path cannot bypass policy.

The broker's security boundary is the Broker.run() method, which enforces
policy authorization BEFORE calling the dispatcher. This test verifies the
complete external authority path — from manifest submission through policy
evaluation to dispatch — cannot bypass the policy gate.

The question is NOT whether Python code can technically import adapters.
The question is whether a caller using the supported external authority path
(Broker.run) can bypass policy enforcement and cause unauthorized execution.
"""

from __future__ import annotations

import pytest

from hive_broker.adapters import (
    AdapterError,
    dispatch,
)
from hive_broker.errors import BrokerError, PolicyError


class TestExternalAuthorityPath:
    """Verify Broker.run enforces policy before dispatch."""

    def _broker(self, tmp_path):
        """Create a minimal broker for testing."""
        from hive_broker import Broker
        state_root = tmp_path / "state"
        log_root = tmp_path / "log"
        state_root.mkdir(parents=True, exist_ok=True)
        log_root.mkdir(parents=True, exist_ok=True)
        return Broker(state_root, log_root)

    def _valid_manifest(self, intent_name, required_caps, allowed_actions):
        """Build a valid task manifest per hive_broker/schema.py and intents.py."""
        return {
            "schema_version": 1,
            "task_id": "test-task-001",
            "requestor": "test-service",
            "intent": intent_name,
            "target_services": ["hive"],
            "required_capabilities": required_caps,
            "allowed_actions": allowed_actions,
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 5,
            "audit_level": "normal",
        }

    def test_broker_allows_read_only_actions(self, tmp_path):
        """Broker.run allows read-only actions through all gates."""
        broker = self._broker(tmp_path)
        manifest = self._valid_manifest("list-services", ["service.list"], ["service.list"])
        result = broker.run(manifest)
        assert result["status"] in ("success", "failure")
        assert result.get("policy_decision") == "ALLOW"
        assert result.get("execution_performed") is True

    def test_capability_advertisement_is_first_gate(self, tmp_path):
        """required_capabilities must be subset of advertised BROKER_CAPABILITIES."""
        broker = self._broker(tmp_path)
        # unknown.capability is not advertised — validate_task_manifest raises
        # CapabilityError, which propagates uncaught from Broker.run.
        # Security property: no adapter dispatch occurs.
        manifest = self._valid_manifest(
            "list-services",
            ["unknown.capability"],
            ["unknown.capability"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_intent_gate_restricts_allowed_actions(self, tmp_path):
        """Intent lookup restricts allowed_actions — vault.status not in list-services intent."""
        broker = self._broker(tmp_path)
        # Both service.list and vault.status are advertised capabilities
        # But list-services intent only allows ["service.list"]
        # validate_task_manifest raises ManifestError, propagates uncaught.
        # Security property: no adapter dispatch occurs.
        manifest = self._valid_manifest(
            "list-services",
            ["service.list", "vault.status"],
            ["service.list", "vault.status"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_mutating_action_not_advertised_so_rejected_early(self, tmp_path):
        """service.start is not in BROKER_CAPABILITIES — rejected at advertisement gate."""
        broker = self._broker(tmp_path)
        manifest = self._valid_manifest(
            "inspect-service-status",
            ["service.start"],
            ["service.start"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_vault_secret_get_not_advertised(self, tmp_path):
        """vault.secret.get is not in BROKER_CAPABILITIES — rejected at advertisement gate."""
        broker = self._broker(tmp_path)
        manifest = self._valid_manifest(
            "inspect-vault-status",
            ["vault.secret.get"],
            ["vault.secret.get"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_update_apply_not_advertised(self, tmp_path):
        """update.apply is not in BROKER_CAPABILITIES — rejected at advertisement gate."""
        broker = self._broker(tmp_path)
        manifest = self._valid_manifest(
            "inspect-update-status",
            ["update.apply"],
            ["update.apply"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_recovery_restore_not_advertised(self, tmp_path):
        """recovery.restore is not in BROKER_CAPABILITIES — rejected at advertisement gate."""
        broker = self._broker(tmp_path)
        manifest = self._valid_manifest(
            "diagnose-recovery-state",
            ["recovery.restore"],
            ["recovery.restore"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_mixed_manifest_rejected_at_intent_gate(self, tmp_path):
        """Manifest with one valid and one unauthorized action is fully denied."""
        broker = self._broker(tmp_path)
        # service.list is valid for list-services intent
        # service.start is not advertised at all
        manifest = self._valid_manifest(
            "list-services",
            ["service.list", "service.start"],
            ["service.list", "service.start"]
        )
        with pytest.raises(BrokerError):
            broker.run(manifest)

    def test_all_advertised_capabilities_are_read_only(self, tmp_path):
        """BROKER_CAPABILITIES contains only read-only (non-mutating) capabilities."""
        from hive_broker.capabilities import BROKER_CAPABILITIES
        for cap in BROKER_CAPABILITIES:
            assert cap.mutation is False, (
                f"Capability {cap.name} is marked as mutating"
            )

    def test_no_mutating_capability_advertised(self, tmp_path):
        """No mutating/destructive capability exists in advertised set."""
        from hive_broker.capabilities import _CAPABILITY_NAMES
        mutating = {
            "service.start", "service.stop", "service.restart",
            "service.kill", "service.remove", "service.disable",
            "vault.secret.get", "vault.secret.read",
            "update.apply", "update.force",
            "recovery.restore", "recovery.reset",
        }
        for cap in mutating:
            assert cap not in _CAPABILITY_NAMES, (
                f"Mutating capability {cap} should not be advertised"
            )

    def test_all_intents_are_read_only(self, tmp_path):
        """All intents except stop-broker-task are read_only=True."""
        from hive_broker.intents import _INTENTS
        for name, intent in _INTENTS.items():
            if name == "stop-broker-task":
                assert intent.read_only is False
            else:
                assert intent.read_only is True, (
                    f"Intent {name} is not read-only"
                )

    def test_no_intent_exposes_mutating_capabilities(self, tmp_path):
        """No intent in the registry exposes mutating/destructive capabilities."""
        from hive_broker.intents import _INTENTS
        mutating = {
            "service.start", "service.stop", "service.restart",
            "service.kill", "service.remove", "service.disable",
            "vault.secret.get", "vault.secret.read",
            "update.apply", "update.force",
            "recovery.restore", "recovery.reset",
        }
        for name, intent in _INTENTS.items():
            for action in intent.allowed_actions:
                assert action not in mutating, (
                    f"Intent {name} exposes mutating capability {action}"
                )

    def test_validator_has_intent_gate_before_policy(self):
        """validate_task_manifest checks intent before returning to Broker.run."""
        from hive_broker.validator import validate_task_manifest
        import inspect

        src = inspect.getsource(validate_task_manifest)
        # get_intent must be in the validator
        assert "get_intent" in src
        # validate_actions_for_policy is NOT in validator — it's in Broker.run
        assert "validate_actions_for_policy" not in src, (
            "validate_task_manifest should not call validate_actions_for_policy"
        )

    def test_broker_has_validator_then_policy_then_dispatch(self):
        """Broker.run orders: validate_task_manifest -> validate_actions_for_policy -> dispatcher.run."""
        from hive_broker import Broker
        import inspect

        src = inspect.getsource(Broker.run)
        validate_idx = src.find("validate_task_manifest")
        policy_idx = src.find("validate_actions_for_policy")
        dispatch_idx = src.find("self.dispatcher.run")
        assert validate_idx > 0, "validate_task_manifest not found"
        assert policy_idx > 0, "validate_actions_for_policy not found"
        assert dispatch_idx > 0, "dispatcher.run not found"
        assert validate_idx < policy_idx < dispatch_idx, (
            "order must be: validate -> policy -> dispatch"
        )

    def test_dispatcher_only_reads_allowed_actions(self):
        """Dispatcher.run source only dispatches manifest['allowed_actions']."""
        from hive_broker.dispatcher import Dispatcher
        import inspect

        src = inspect.getsource(Dispatcher.run)
        assert "allowed_actions" in src
        assert "dispatch_adapter" in src
        assert "getattr" not in src
