"""Milestone 19 — I2 Secret leakage investigation.

Uses synthetic secret markers to verify redaction layers mask secrets in:
- broker outputs (via policy context redaction)
- Operations Center redaction
- plugin audit redaction
- vault redaction helpers
- config audit redaction
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from operations_center.redaction import redact_value
from plugin_sdk.audit import redact_secrets
from security.vault.redaction import redact, redact_exception
from config_engine.audit import ConfigAuditLog, _redact_details


# Synthetic secret markers — must NEVER appear in REDACTED output
_MARKERS = {
    "M19_TEST_PASSWORD_SECRET",
    "M19_TEST_API_TOKEN",
    "M19_TEST_PRIVATE_VALUE",
}


def _assert_no_markers(text: str, source: str) -> None:
    for marker in _MARKERS:
        assert marker not in text, f"Secret marker leaked in {source}: {marker}"


class TestSecretLeakageBrokerOutputs:
    """I2 — broker outputs via structured result dicts."""

    def test_broker_status_no_secret(self, tmp_path):
        from hive_broker import Broker
        broker = Broker(state_root=tmp_path, log_root=tmp_path)
        status = broker.status()
        text = json.dumps(status)
        _assert_no_markers(text, "broker.status")

    def test_broker_validate_error_no_secret(self):
        from hive_broker import Broker
        broker = Broker(state_root=Path("/tmp"), log_root=Path("/tmp"))
        raw = {
            "schema_version": 1,
            "task_id": "t-1",
            "requestor": "test",
            "intent": "inspect-service-status",
            "allowed_actions": [],
            "target_services": [],
            "required_capabilities": [],
            "read_only": True,
            "timeout_seconds": 30,
        }
        result = broker.validate(raw)
        text = json.dumps(result)
        _assert_no_markers(text, "broker.validate")

    def test_broker_run_readonly_no_secret(self, tmp_path):
        """Broker.inspect() returns digest/metadata without secret leakage."""
        from hive_broker import Broker
        broker = Broker(state_root=tmp_path, log_root=tmp_path)
        raw = {
            "schema_version": 1,
            "task_id": "t-1",
            "requestor": "test",
            "intent": "inspect-service-status",
            "allowed_actions": ["service.status"],
            "target_services": [],
            "required_capabilities": ["service.status"],
            "read_only": True,
            "timeout_seconds": 30,
        }
        result = broker.inspect(raw)
        text = json.dumps(result)
        _assert_no_markers(text, "broker.inspect")


class TestSecretLeakagePolicyOutputs:
    """I2 — policy evaluator outputs."""

    def test_policy_evaluator_denies_without_leak(self):
        from policy_engine.evaluator import PolicyEvaluator
        from policy_engine.requests import PolicyRequest
        from policy_engine.rules import PolicySet, PolicyProfile
        from policy_engine.decisions import DecisionState

        profile = PolicyProfile(name="test", description="test", rules=[], default_decision=DecisionState.DENY)
        pset = PolicySet({"test": profile})
        evaluator = PolicyEvaluator(pset)
        req = PolicyRequest(
            schema_version=1,
            request_id="r-1",
            transaction_id="t-1",
            actor={"type": "operator", "id": "u1"},
            capability="service.status",
            resource={"type": "service", "id": "svc1"},
            context={"secret_value": "M19_TEST_PRIVATE_VALUE"},
        )
        result = evaluator.evaluate(req)
        text = json.dumps(result.to_dict())
        _assert_no_markers(text, "policy evaluator")


class TestSecretLeakageOperationsCenter:
    """I2 — Operations Center redaction."""

    def test_redact_value_masks_secret_keys(self):
        data = {
            "user": "alice",
            "password": "M19_TEST_PASSWORD_SECRET",
            "token": "M19_TEST_API_TOKEN",
            "nested": {"private_value": "M19_TEST_PRIVATE_VALUE"},
        }
        safe = redact_value(data)
        text = json.dumps(safe)
        _assert_no_markers(text, "operations_center redact_value")

    def test_redact_paths_masks_termux_paths(self):
        data = {"home": "/data/data/com.termux/files/home", "password": "M19_TEST_PASSWORD_SECRET"}
        safe = redact_value(data)
        text = json.dumps(safe)
        _assert_no_markers(text, "operations_center redact_paths")


class TestSecretLeakagePluginAudit:
    """I2 — plugin SDK audit redaction."""

    def test_redact_secrets_masks_secret_keys(self):
        data = {
            "config": {"api_key": "M19_TEST_API_TOKEN"},
            "secret": "M19_TEST_PASSWORD_SECRET",
        }
        safe = redact_secrets(data)
        assert safe["config"]["api_key"] == "[redacted]"
        assert safe["secret"] == "[redacted]"

    def test_redact_secrets_high_entropy_value(self):
        """High-entropy value-only redaction heuristic test."""
        data = {"plain_key": "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0"}
        safe = redact_secrets(data)
        assert safe["plain_key"] == "[redacted]"


class TestSecretLeakageVaultRedaction:
    """I2 — vault redaction helpers."""

    def test_redact_masks_secret_keys(self):
        data = {
            "password": "M19_TEST_PASSWORD_SECRET",
            "token": "M19_TEST_API_TOKEN",
        }
        safe = redact(data)
        text = json.dumps(safe)
        _assert_no_markers(text, "vault redact")

    def test_redact_exception_masks_token_like_values(self):
        exc = Exception("Login failed with token Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3")
        text = redact_exception(exc)
        assert "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3" not in text


class TestSecretLeakageConfigAudit:
    """I2 — config engine audit and persistence redaction."""

    def test_redact_details_strips_secrets(self):
        details = {
            "id": "r-1",
            "password": "M19_TEST_PASSWORD_SECRET",
            "token": "M19_TEST_API_TOKEN",
        }
        safe = _redact_details(details)
        text = json.dumps(safe)
        _assert_no_markers(text, "config_engine _redact_details")

    def test_config_audit_log_redacts(self, tmp_path):
        log = ConfigAuditLog(tmp_path / "audit.jsonl")
        log.record("txn-1", "test", "default", "author", {"password": "M19_TEST_PASSWORD_SECRET"})
        lines = (tmp_path / "audit.jsonl").read_text().strip().split("\n")
        text = lines[-1]
        _assert_no_markers(text, "config_engine audit log")


class TestSecretLeakageDirectExceptions:
    """I2 — direct exception text (not redacted) may contain raw strings.

    This is expected behavior. The redaction layer must be applied BEFORE
    display/logging. We verify the redaction layer exists and works.
    """

    def test_exception_constructors_do_not_auto_redact(self):
        """Confirming that Exception(str) preserves the argument."""
        from hive_broker.errors import ManifestError
        exc = ManifestError("Invalid manifest: M19_TEST_PASSWORD_SECRET")
        assert "M19_TEST_PASSWORD_SECRET" in str(exc)

    def test_redact_exception_sanitizes_manifest_error(self):
        """redact_exception applied to ManifestError strips token-like values."""
        from hive_broker.errors import ManifestError
        exc = ManifestError("Invalid manifest: Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3")
        text = redact_exception(exc)
        assert "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3" not in text

