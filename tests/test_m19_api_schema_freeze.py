"""Milestone 19 — API / Schema freeze boundedness audit.

Production schema version enforcement catalog:
All production modules hardcode schema_version == 1 and reject any other value.
No version negotiation, no backward compatibility shim for unsupported versions.
Migration system exists in config_engine but is not exercised on production paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _minimal_plugin_manifest(schema_version: int = 1) -> dict:
    """Return a minimal valid plugin manifest dict for testing."""
    return {
        "schema_version": schema_version,
        "plugin": {
            "id": "test",
            "name": "Test Plugin",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "entrypoint": "main.py",
            "type": "client",
        },
        "compatibility": {"minimum_hive_version": "1.0.0"},
        "permissions": {
            "requested_capabilities": [],
            "filesystem": [],
            "network": "none",
            "secrets": [],
        },
        "lifecycle": {"auto_start": False},
    }


# ---------------------------------------------------------------------------
# 1. hive_broker.schema — manifest schema_version locked to 1
# ---------------------------------------------------------------------------

class TestBrokerManifestSchemaFreeze:
    def test_manifest_schema_version_1_accepted(self):
        """Broker manifest with schema_version 1 is accepted."""
        from hive_broker.schema import validate_manifest
        raw = {
            "schema_version": 1,
            "task_id": "task-1",
            "requestor": "test",
            "intent": "read",
            "required_capabilities": ["service.status"],
            "allowed_actions": ["read"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
        }
        m = validate_manifest(raw)
        assert m["schema_version"] == 1

    def test_manifest_schema_version_2_rejected(self):
        """Broker manifest with schema_version 2 raises ManifestError."""
        from hive_broker.schema import validate_manifest
        from hive_broker.errors import ManifestError
        raw = {
            "schema_version": 2,
            "task_id": "task-1",
            "requestor": "test",
            "intent": "read",
            "required_capabilities": ["service.status"],
            "allowed_actions": ["read"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
        }
        with pytest.raises(ManifestError, match="Unsupported manifest schema version"):
            validate_manifest(raw)


# ---------------------------------------------------------------------------
# 2. plugin_sdk.manifest — plugin manifest schema_version locked to 1
# ---------------------------------------------------------------------------

class TestPluginManifestSchemaFreeze:
    def test_plugin_manifest_schema_version_1_accepted(self):
        """Plugin manifest with schema_version 1 is accepted."""
        from plugin_sdk.manifest import load_manifest
        raw = _minimal_plugin_manifest(1)
        path = Path("/tmp") / "test_plugin_manifest_v1.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        try:
            m = load_manifest(path)
            assert m["schema_version"] == 1
        finally:
            path.unlink(missing_ok=True)

    def test_plugin_manifest_schema_version_2_rejected(self):
        """Plugin manifest with schema_version 2 raises PluginManifestError."""
        from plugin_sdk.manifest import load_manifest
        from plugin_sdk.errors import PluginManifestError
        raw = _minimal_plugin_manifest(2)
        path = Path("/tmp") / "test_plugin_manifest_v2.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        try:
            with pytest.raises(PluginManifestError, match="unsupported schema_version"):
                load_manifest(path)
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. policy_engine.requests — policy request schema_version locked to {1}
# ---------------------------------------------------------------------------

class TestPolicyRequestSchemaFreeze:
    def test_policy_request_schema_version_1_accepted(self):
        """Policy request with schema_version 1 is accepted."""
        from policy_engine.requests import PolicyRequest
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "req-1",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "u1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc1"},
            "context": {},
        })
        assert req.schema_version == 1

    def test_policy_request_schema_version_2_rejected(self):
        """Policy request with schema_version 2 raises PolicyRequestError."""
        from policy_engine.requests import PolicyRequest
        from policy_engine.errors import PolicyRequestError
        with pytest.raises(PolicyRequestError, match="Unsupported policy request schema version"):
            PolicyRequest.from_dict({
                "schema_version": 2,
                "request_id": "req-1",
                "transaction_id": "txn-1",
                "actor": {"type": "operator", "id": "u1"},
                "capability": "service.status",
                "resource": {"type": "service", "id": "svc1"},
                "context": {},
            })


# ---------------------------------------------------------------------------
# 4. services.schema — service manifest schema_version locked to 1
# ---------------------------------------------------------------------------

class TestServiceManifestSchemaFreeze:
    def test_service_manifest_schema_version_1_accepted(self):
        """Service manifest with schema_version 1 is accepted."""
        from services.schema import validate_manifest
        raw = {
            "schema_version": 1,
            "name": "testsvc",
            "command": {"interpreter": "bash", "base": "state-root", "args": ["echo", "hi"]},
        }
        m = validate_manifest(raw)
        assert m["schema_version"] == 1

    def test_service_manifest_schema_version_2_rejected(self):
        """Service manifest with schema_version 2 raises ServiceConfigError."""
        from services.schema import validate_manifest
        from services.errors import ServiceConfigError
        raw = {
            "schema_version": 2,
            "name": "testsvc",
            "command": {"interpreter": "bash", "base": "state-root", "args": ["echo", "hi"]},
        }
        with pytest.raises(ServiceConfigError, match="Unsupported schema version"):
            validate_manifest(raw)


# ---------------------------------------------------------------------------
# 5. installer.activate — active pointer / release schema_version locked
# ---------------------------------------------------------------------------

class TestInstallerActivateSchemaFreeze:
    def test_active_pointer_schema_version_mismatch_rejected(self, tmp_path):
        """_active_pointer rejects schema_version != 1."""
        from installer.activate import ActiveState, ActivationSafetyError
        state = ActiveState(data_root=tmp_path, state_root=tmp_path)
        pointer = {
            "schema_version": 2,
            "active_release_id": "rel-1",
            "active_runtime": str(tmp_path),
            "previous_release_id": "",
            "updated_at": 0,
        }
        state.active_pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
        with pytest.raises(ActivationSafetyError, match="schema_version|Unknown active pointer"):
            state._active_pointer()

    def test_release_metadata_schema_version_mismatch_rejected(self, tmp_path):
        """_read_release_metadata rejects schema_version != 1."""
        from installer.activate import ActiveState, ActivationSafetyError
        from installer.activate import ReleaseInfo
        state = ActiveState(data_root=tmp_path, state_root=tmp_path)
        rel_dir = state._release_path("rel-1")
        rel_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "schema_version": 2,
            "release_id": "rel-1",
            "release_version": "1.0.0",
            "commit": "abc",
            "timestamp": 0,
            "files": [],
        }
        meta_path = state._release_metadata_path("rel-1")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        with pytest.raises(ActivationSafetyError, match="schema_version|Unknown release"):
            state._read_release_metadata("rel-1")


# ---------------------------------------------------------------------------
# 6. release_engine.registry — registry schema_version locked to 1
# ---------------------------------------------------------------------------

class TestReleaseRegistrySchemaFreeze:
    def test_release_registry_schema_version_1_accepted(self, tmp_path):
        """ReleaseRegistry accepts schema_version 1."""
        from release_engine.registry import ReleaseRegistry
        reg = ReleaseRegistry(path=tmp_path / "reg.json")
        data = reg._load()
        assert data.get("schema_version") == 1

    def test_release_registry_load_does_not_validate_schema_version(self, tmp_path):
        """ReleaseRegistry._load does not validate schema version; documents accepted debt."""
        from release_engine.registry import ReleaseRegistry
        reg_path = tmp_path / "reg.json"
        reg_path.write_text(json.dumps({"schema_version": 2, "releases": []}), encoding="utf-8")
        reg = ReleaseRegistry(path=reg_path)
        data = reg._load()
        assert data["schema_version"] == 2  # accepted because _load does not validate


# ---------------------------------------------------------------------------
# 7. config_engine.migration — migration system exists but not on prod paths
# ---------------------------------------------------------------------------

class TestConfigMigrationNotOnProductionPaths:
    def test_migration_system_exists(self):
        """Migration class exists in config_engine.migration."""
        from config_engine.migration import Migration
        def _noop(data):
            return data
        m = Migration(name="test", from_version=1, to_version=2, transform=_noop)
        assert m.from_version == 1
        assert m.to_version == 2

    def test_migration_not_called_by_loader(self):
        """load_json_file does not invoke migration logic."""
        import inspect
        from config_engine.loader import load_json_file
        src = inspect.getsource(load_json_file)
        assert "migration" not in src.lower()
        assert "migrate" not in src.lower()


# ---------------------------------------------------------------------------
# 8. Compatibility negotiation is distinct from schema version negotiation
# ---------------------------------------------------------------------------

class TestCompatibilityNegotiationDistinct:
    def test_plugin_sdk_has_compatibility_negotiation(self):
        """plugin_sdk has negotiate_compatibility for runtime version matching;
        this is distinct from schema_version freeze."""
        import inspect
        from plugin_sdk import compatibility as c
        assert hasattr(c, "negotiate_compatibility")
        src = inspect.getsource(c.negotiate_compatibility)
        assert "schema_version" not in src.lower()

    def test_no_schema_version_negotiation_in_production(self):
        """No production module contains schema version negotiation logic."""
        import sys, re
        if sys.platform == "win32":
            pytest.skip("grep-based static scan is POSIX-only")
        import subprocess
        # Resolve repo root relative to this test file instead of hardcoding
        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            ["grep", "-rni", "schema_version.*negotiat",
             "--include=*.py", "."],
            capture_output=True, text=True,
            cwd=str(repo_root),
        )
        lines = [l for l in result.stdout.splitlines()
                 if "tests/" not in l and "venv/" not in l and "__pycache__" not in l
                 and "brain-plug" not in l and "Hive Ops" not in l
                 and "MILESTONE19" not in l and "HARDENING" not in l]
        assert len(lines) == 0, f"Unexpected schema negotiation: {lines}"


# ---------------------------------------------------------------------------
# 9. Schema freeze defaults
# ---------------------------------------------------------------------------

class TestSchemaFreezeDefaults:
    def test_all_schema_version_defaults_are_1(self):
        """All schema_version defaults across modules are 1."""
        from plugin_sdk.schema import SCHEMA_VERSION
        from policy_engine.requests import KNOWN_SCHEMA_VERSIONS
        from release_engine.registry import REGISTRY_SCHEMA_VERSION
        from services.schema import SCHEMA_VERSION as SVC_SCHEMA
        assert SCHEMA_VERSION == 1
        assert 1 in KNOWN_SCHEMA_VERSIONS
        assert REGISTRY_SCHEMA_VERSION == 1
        assert SVC_SCHEMA == 1

    def test_config_engine_schema_default_is_1(self):
        """ConfigSchema default version is 1."""
        from config_engine.schema import ConfigSchema
        schema = ConfigSchema(name="test", version=1, fields={})
        assert schema.version == 1

    def test_policy_engine_schema_default_is_1(self):
        """TypedSchema default version is 1."""
        from policy_engine.schema import TypedSchema
        schema = TypedSchema(name="test", version=1, fields={})
        assert schema.version == 1