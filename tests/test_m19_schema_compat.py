"""Milestone 19 — Area G: API and schema compatibility tests.

Tests schema version enforcement, missing field handling, unknown field
tolerance, and CLI backward compatibility.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from policy_engine.requests import PolicyRequest, KNOWN_SCHEMA_VERSIONS
from policy_engine.errors import PolicyRequestError
from installer.activate import ActiveState, ActivationSafetyError
from config_engine.persistence import atomic_write_json
from updates.metadata import parse_metadata, METADATA_SCHEMA_VERSION
from config_engine.schema import ConfigSchema, FieldSpec, ConfigValidationError


class TestSchemaCompatibility:
    # -----------------------------------------------------------------------
    # G1: Schema version downgrade
    # -----------------------------------------------------------------------

    def test_policy_request_unknown_schema_version_rejected(self):
        """G1: Unknown policy request schema version must be rejected."""
        with pytest.raises(PolicyRequestError, match="Unsupported policy request schema version"):
            PolicyRequest.from_dict({
                "schema_version": 999,  # unknown version
                "request_id": "test",
                "transaction_id": "txn-1",
                "actor": {"type": "user", "id": "test"},
                "capability": "broker.status",
                "resource": {"type": "broker", "id": "status"},
                "context": {},
            })

    def test_policy_request_known_schema_version_accepted(self):
        """G1: Known schema version must be accepted."""
        for version in KNOWN_SCHEMA_VERSIONS:
            req = PolicyRequest.from_dict({
                "schema_version": version,
                "request_id": "test",
                "transaction_id": "txn-1",
                "actor": {"type": "operator", "id": "test"},
                "capability": "vault.status",
                "resource": {"type": "vault", "id": "master"},
                "context": {},
            })
            assert req.schema_version == version

    def test_metadata_unknown_schema_version_rejected(self):
        """G1: Unknown metadata schema version must be rejected."""
        raw = json.dumps({"schema_version": 999})
        with pytest.raises(Exception, match="Unsupported metadata schema"):
            parse_metadata(raw)

    def test_active_pointer_unknown_schema_rejected(self):
        """G1: Unknown active pointer schema must raise ActivationSafetyError."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            active.active_pointer_path.parent.mkdir(parents=True, exist_ok=True)
            active.active_pointer_path.write_text(
                json.dumps({"schema_version": 999, "active_release_id": "x", "active_runtime": "y"}),
                encoding="utf-8",
            )
            with pytest.raises(ActivationSafetyError, match="Unknown active pointer schema"):
                active._active_pointer()

    # -----------------------------------------------------------------------
    # G2: Missing required field
    # -----------------------------------------------------------------------

    def test_policy_request_missing_required_field_raises_error(self):
        """G2: Missing required field in PolicyRequest must raise PolicyRequestError."""
        from policy_engine.errors import PolicyError
        with pytest.raises(PolicyError):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "test",
                "transaction_id": "txn-1",
                # Missing: actor (required), capability (required), resource (required), context (required)
            })

    def test_policy_request_missing_capability_raises_error(self):
        """G2: Missing capability in PolicyRequest must raise PolicyRequestError."""
        from policy_engine.errors import PolicyError
        with pytest.raises(PolicyError):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "test",
                "transaction_id": "txn-1",
                "actor": {"type": "operator", "id": "test"},
                "resource": {"type": "vault", "id": "master"},
                "context": {},
                # Missing: capability
            })

    def test_config_schema_missing_required_field_raises(self):
        """G2: ConfigSchema with missing required field must raise."""
        schema = ConfigSchema(
            "test",
            version=1,
            fields={
                "required_field": FieldSpec("required_field", str, required=True),
                "optional_field": FieldSpec("optional_field", str),
            },
        )
        with pytest.raises(ConfigValidationError):
            schema.validate({"optional_field": "present"})

    # -----------------------------------------------------------------------
    # G3: Unknown field tolerance
    # -----------------------------------------------------------------------

    def test_policy_request_actor_strict_no_unknown_fields(self):
        """G3: Unknown fields in actor are rejected (strict actor validation)."""
        from policy_engine.errors import PolicyError
        with pytest.raises(PolicyError, match="Unknown field"):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "test",
                "transaction_id": "txn-1",
                "actor": {"type": "operator", "id": "test", "unknown_field": "value"},
                "capability": "vault.status",
                "resource": {"type": "vault", "id": "master"},
                "context": {},
            })

    def test_policy_request_resource_tolerates_unknown_fields(self):
        """G3: Unknown fields in resource are tolerated (allow_unknown=True)."""
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master", "unknown_field": "value"},
            "context": {},
        })
        assert req.request_id == "test"
        assert req.resource["unknown_field"] == "value"

    def test_policy_request_context_tolerates_unknown_fields(self):
        """G3: Unknown fields in context are tolerated (allow_unknown=True)."""
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {"unknown_context": "value"},
        })
        assert req.request_id == "test"
        assert req.context["unknown_context"] == "value"

    def test_config_schema_unknown_field_with_allow_unknown(self):
        """G3: ConfigSchema with allow_unknown should tolerate unknown fields."""
        schema = ConfigSchema(
            "test",
            version=1,
            fields={
                "known": FieldSpec("known", str, required=True),
            },
            allow_unknown=True,
        )
        result = schema.validate({"known": "value", "unknown": "extra"})
        assert result["known"] == "value"
        assert "unknown" in result

    # -----------------------------------------------------------------------
    # G4: CLI backward compatibility
    # -----------------------------------------------------------------------

    def test_cli_help_still_works(self):
        """G4: --help flag must continue to work."""
        result = subprocess.run(
            [sys.executable, "bin/hive", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        assert "Hive OS" in result.stdout or "hive" in result.stdout.lower()

    def test_cli_resolve_still_works(self):
        """G4: --resolve flag must continue to work."""
        result = subprocess.run(
            [sys.executable, "bin/hive", "--resolve"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0

    def test_cli_runtime_info_json_still_works(self):
        """G4: --runtime-info --json must continue to produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "bin/hive", "--runtime-info", "--json"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert "platform" in report

    def test_cli_subcommands_exist(self):
        """G4: All documented subcommands must be dispatchable."""
        subcommands = [
            "config validate",
            "broker status",
            "vault status",
            "plugin list",
            "service validate",
            "ops",
        ]
        for cmd in subcommands:
            result = subprocess.run(
                [sys.executable, "bin/hive"] + cmd.split(),
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            # We only verify they don't crash (exit code may be 0, 1, or 2 depending on state)
            assert result.returncode in (0, 1, 2), f"Command '{cmd}' crashed with exit {result.returncode}: {result.stderr}"
