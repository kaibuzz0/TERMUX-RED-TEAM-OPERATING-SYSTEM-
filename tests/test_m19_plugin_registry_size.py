"""Milestone 19 — Plugin registry/SDK size boundedness audit.

Production plugin registry / SDK size bounds catalog:
- plugin_sdk.schema.PLUGIN_ID_MAX_LENGTH = 128 — enforced in plugin_sdk.manifest._validate_plugin_id()
- plugin_sdk.schema.MAX_RESULT_SIZE = 256 KiB — enforced in plugin_sdk.broker_client._validate_result()
- plugin_sdk.schema.MAX_BUNDLE_SIZE = 10 MiB — schema constant only; NO production enforcement
- plugin_sdk.schema.MAX_BUNDLE_FILES = 1000 — schema constant only; NO production enforcement
- plugin_sdk.schema.MAX_BUNDLE_PATH_LENGTH = 256 — schema constant only; NO production enforcement
- plugin_sdk.schema.MAX_STDOUT_SIZE = 64 KiB — schema constant only; NO production enforcement
- plugin_sdk.schema.MAX_STDERR_SIZE = 64 KiB — schema constant only; NO production enforcement
- release_engine.plugin_registry.PersistentPluginRegistry — NO explicit plugin count limit
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. PLUGIN_ID_MAX_LENGTH
# ---------------------------------------------------------------------------

class TestPluginIdMaxLengthBounded:
    def test_accepts_exactly_max_length(self):
        """Plugin ID of exactly 128 characters is accepted."""
        from plugin_sdk.manifest import _validate_plugin_id
        raw = "a" * 128
        assert _validate_plugin_id(raw) == raw

    def test_rejects_max_plus_1(self):
        """Plugin ID of 129 characters is rejected."""
        from plugin_sdk.manifest import _validate_plugin_id
        from plugin_sdk.errors import PluginManifestError
        with pytest.raises(PluginManifestError, match="exceeds 128 characters"):
            _validate_plugin_id("a" * 129)

    def test_default_value_is_128(self):
        """PLUGIN_ID_MAX_LENGTH default is 128."""
        from plugin_sdk.schema import PLUGIN_ID_MAX_LENGTH
        assert PLUGIN_ID_MAX_LENGTH == 128


# ---------------------------------------------------------------------------
# 2. MAX_RESULT_SIZE
# ---------------------------------------------------------------------------

class TestMaxResultSizeBounded:
    def test_broker_result_size_constant_enforced_in_source(self):
        """MAX_RESULT_SIZE is checked in broker_client against str(raw) length."""
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.schema import MAX_RESULT_SIZE
        identity = PluginIdentity(
            plugin_id="test",
            plugin_version="1.0.0",
            manifest_digest="sha256:" + "a" * 64,
            installation_id="install-1",
        )
        # Simulate a backend returning a very large dict
        big_data = {"payload": "x" * (MAX_RESULT_SIZE + 100)}
        client = PluginClient(
            identity=identity,
            granted_capabilities=["read"],
            backend=lambda cap, ctx: {"status": "ok", "data": big_data},
        )
        from plugin_sdk.errors import PluginExecutionError
        with pytest.raises(PluginExecutionError, match="exceeded size limit"):
            client.request("read")

    def test_default_value_is_256_kib(self):
        """MAX_RESULT_SIZE default is 256 KiB."""
        from plugin_sdk.schema import MAX_RESULT_SIZE
        assert MAX_RESULT_SIZE == 256 * 1024

    def test_enforced_in_broker_client_source(self):
        """MAX_RESULT_SIZE is referenced in broker_client production code."""
        import inspect
        from plugin_sdk import broker_client as bc
        src = inspect.getsource(bc)
        assert "MAX_RESULT_SIZE" in src


# ---------------------------------------------------------------------------
# 3. MAX_BUNDLE_SIZE — schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestMaxBundleSizeSchemaOnly:
    def test_constant_defined(self):
        """MAX_BUNDLE_SIZE is defined in plugin_sdk.schema."""
        from plugin_sdk.schema import MAX_BUNDLE_SIZE
        assert MAX_BUNDLE_SIZE == 10 * 1024 * 1024

    def test_no_production_code_enforces_max_bundle_size(self):
        """No production module reads MAX_BUNDLE_SIZE to reject bundles."""
        import inspect
        from plugin_sdk import schema as s
        src = inspect.getsource(s)
        # The constant is defined but never consumed in this module
        assert "MAX_BUNDLE_SIZE" in src
        # Higher layers (loader, manifest) do not reference it
        import plugin_sdk.loader as l
        loader_src = inspect.getsource(l)
        assert "MAX_BUNDLE_SIZE" not in loader_src
        import plugin_sdk.manifest as m
        manifest_src = inspect.getsource(m)
        assert "MAX_BUNDLE_SIZE" not in manifest_src


# ---------------------------------------------------------------------------
# 4. MAX_BUNDLE_FILES — schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestMaxBundleFilesSchemaOnly:
    def test_constant_defined(self):
        """MAX_BUNDLE_FILES is defined in plugin_sdk.schema."""
        from plugin_sdk.schema import MAX_BUNDLE_FILES
        assert MAX_BUNDLE_FILES == 1000

    def test_no_production_code_enforces_max_bundle_files(self):
        """No production module reads MAX_BUNDLE_FILES to reject bundles."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_BUNDLE_FILES" in inspect.getsource(s)
        import plugin_sdk.loader as l
        assert "MAX_BUNDLE_FILES" not in inspect.getsource(l)
        import plugin_sdk.manifest as m
        assert "MAX_BUNDLE_FILES" not in inspect.getsource(m)


# ---------------------------------------------------------------------------
# 5. MAX_BUNDLE_PATH_LENGTH — schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestMaxBundlePathLengthSchemaOnly:
    def test_constant_defined(self):
        """MAX_BUNDLE_PATH_LENGTH is defined in plugin_sdk.schema."""
        from plugin_sdk.schema import MAX_BUNDLE_PATH_LENGTH
        assert MAX_BUNDLE_PATH_LENGTH == 256

    def test_no_production_code_enforces_max_bundle_path_length(self):
        """No production module reads MAX_BUNDLE_PATH_LENGTH."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_BUNDLE_PATH_LENGTH" in inspect.getsource(s)
        import plugin_sdk.loader as l
        assert "MAX_BUNDLE_PATH_LENGTH" not in inspect.getsource(l)


# ---------------------------------------------------------------------------
# 6. MAX_STDOUT_SIZE / MAX_STDERR_SIZE — schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestMaxStdoutStderrSchemaOnly:
    def test_constants_defined(self):
        """MAX_STDOUT_SIZE and MAX_STDERR_SIZE are defined in plugin_sdk.schema."""
        from plugin_sdk.schema import MAX_STDOUT_SIZE, MAX_STDERR_SIZE
        assert MAX_STDOUT_SIZE == 64 * 1024
        assert MAX_STDERR_SIZE == 64 * 1024

    def test_no_production_code_enforces_max_stdout_size(self):
        """No production module reads MAX_STDOUT_SIZE."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_STDOUT_SIZE" in inspect.getsource(s)
        import plugin_sdk.broker_client as bc
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(bc)

    def test_no_production_code_enforces_max_stderr_size(self):
        """No production module reads MAX_STDERR_SIZE."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_STDERR_SIZE" in inspect.getsource(s)
        import plugin_sdk.broker_client as bc
        assert "MAX_STDERR_SIZE" not in inspect.getsource(bc)


# ---------------------------------------------------------------------------
# 7. PersistentPluginRegistry has no explicit size bound
# ---------------------------------------------------------------------------

class TestPluginRegistryUnbounded:
    def test_registry_accepts_many_plugins(self, tmp_path):
        """PersistentPluginRegistry has no explicit plugin count limit."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
        registry = PersistentPluginRegistry(tmp_path / "registry.json")
        for i in range(500):
            registry.register(PluginRegistryRecord(
                plugin_id=f"plugin-{i:03d}",
                version="1.0.0",
                installation_id=f"install-{i}",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signature_trust="trusted",
                requested_capabilities=[],
                granted_capabilities=[],
                configuration_digest="sha256:" + "c" * 64,
                state="ENABLED",
                install_timestamp="2024-01-01T00:00:00Z",
                publisher=None,
                sdk_compatibility="1.0",
                quarantine_state=None,
            ))
        assert len(registry.list_plugins()) == 500

    def test_registry_file_grows_unbounded(self, tmp_path):
        """Registry JSON file grows with each plugin; no pruning."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
        registry = PersistentPluginRegistry(tmp_path / "registry.json")
        for i in range(200):
            registry.register(PluginRegistryRecord(
                plugin_id=f"plugin-{i:03d}",
                version="1.0.0",
                installation_id=f"install-{i}",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signature_trust="trusted",
                requested_capabilities=[],
                granted_capabilities=[],
                configuration_digest="sha256:" + "c" * 64,
                state="ENABLED",
                install_timestamp="2024-01-01T00:00:00Z",
                publisher=None,
                sdk_compatibility="1.0",
                quarantine_state=None,
            ))
        file_size = registry.path.stat().st_size
        assert file_size > 50_000  # significantly large

    def test_release_registry_also_unbounded(self, tmp_path):
        """ReleaseRegistry similarly has no explicit record count limit."""
        from release_engine.registry import ReleaseRegistry, ReleaseRecord
        reg = ReleaseRegistry(tmp_path / "releases.json")
        for i in range(300):
            reg.register(ReleaseRecord(
                release_id=f"rel-{i:04d}",
                version="1.0.0",
                release_sequence=i,
                channel="stable",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signing_key_id="key-1",
            ))
        assert len(reg.list_releases()) == 300


# ---------------------------------------------------------------------------
# 8. Manifest size in plugin_registry records
# ---------------------------------------------------------------------------

class TestRegistryRecordManifestDigestLength:
    def test_manifest_digest_accepted_at_sha256_length(self, tmp_path):
        """A 64-character hex digest is accepted in registry records."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
        registry = PersistentPluginRegistry(tmp_path / "registry.json")
        digest = "sha256:" + "a" * 64
        registry.register(PluginRegistryRecord(
            plugin_id="test-plugin",
            version="1.0.0",
            installation_id="i1",
            manifest_digest=digest,
            bundle_digest=digest,
            signature_trust="trusted",
            requested_capabilities=[],
            granted_capabilities=[],
            configuration_digest=digest,
            state="ENABLED",
            install_timestamp="2024-01-01T00:00:00Z",
            publisher=None,
            sdk_compatibility="1.0",
            quarantine_state=None,
        ))
        record = registry.get("test-plugin")
        assert record.manifest_digest == digest

    def test_manifest_digest_no_max_length_enforced(self, tmp_path):
        """Registry does not enforce a maximum manifest_digest length."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
        registry = PersistentPluginRegistry(tmp_path / "registry.json")
        long_digest = "sha256:" + "x" * 5000
        registry.register(PluginRegistryRecord(
            plugin_id="long-digest-plugin",
            version="1.0.0",
            installation_id="i2",
            manifest_digest=long_digest,
            bundle_digest=long_digest,
            signature_trust="trusted",
            requested_capabilities=[],
            granted_capabilities=[],
            configuration_digest=long_digest,
            state="ENABLED",
            install_timestamp="2024-01-01T00:00:00Z",
            publisher=None,
            sdk_compatibility="1.0",
            quarantine_state=None,
        ))
        record = registry.get("long-digest-plugin")
        assert record.manifest_digest == long_digest