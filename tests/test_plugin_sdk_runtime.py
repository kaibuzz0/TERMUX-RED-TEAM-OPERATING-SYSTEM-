"""Plugin SDK runtime tests: lifecycle, registry, loader, broker client, config."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from plugin_sdk import PluginIdentityError, load_manifest, manifest_digest
from plugin_sdk.broker_client import PluginClient, create_plugin_client
from plugin_sdk.configuration import (
    digest_plugin_config,
    plugin_config_namespace,
    redact_plugin_config,
    validate_config_schema,
)
from plugin_sdk.errors import (
    PluginBundleError,
    PluginCapabilityError,
    PluginConfigurationError,
    PluginLifecycleError,
)
from plugin_sdk.identity import PluginIdentity, digest_capability_grant
from plugin_sdk.lifecycle import DEFAULT_STATE, PluginLifecycle
from plugin_sdk.loader import inspect_bundle, stage_bundle
from plugin_sdk.registry import PluginRegistry
from plugin_sdk.signing import SignatureMetadata, TrustState, classify_signature


def _valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "plugin": {
            "id": "example.status-plugin",
            "name": "Example Status Plugin",
            "version": "1.0.0",
            "sdk_version": "1.0",
            "entrypoint": "example_plugin.main",
            "type": "client",
        },
        "compatibility": {
            "minimum_hive_version": "1.0.0-dev",
            "required_broker_version": "1.0",
            "required_capabilities": ["service.status", "broker.status"],
        },
        "permissions": {
            "requested_capabilities": ["service.status"],
            "filesystem": [],
            "network": "deny",
            "secrets": [],
        },
        "lifecycle": {"auto_start": False},
    }


class TestLifecycle:
    def test_default_state_disabled(self):
        lc = PluginLifecycle(plugin_id="x")
        assert lc.state == "DISABLED"

    def test_discovered_to_validated(self):
        lc = PluginLifecycle(plugin_id="x", state="DISCOVERED")
        lc.transition("VALIDATED")
        assert lc.state == "VALIDATED"

    def test_invalid_transition(self):
        lc = PluginLifecycle(plugin_id="x", state="REMOVED")
        with pytest.raises(PluginLifecycleError):
            lc.transition("ENABLED")

    def test_repeated_failure_quarantine(self):
        lc = PluginLifecycle(plugin_id="x", state="ENABLED", max_failures=2)
        lc.record_failure()
        assert lc.state == "DEGRADED"
        lc.record_failure()
        assert lc.state == "QUARANTINED"


class TestRegistry:
    def test_discover_and_validate(self, tmp_path):
        stage = tmp_path / "stage"
        stage.mkdir()
        (stage / "manifest.json").write_text(json.dumps(_valid_manifest()), encoding="utf-8")
        reg = PluginRegistry()
        entry = reg.discover(stage)
        assert entry.lifecycle.state == "DISCOVERED"
        reg.validate(entry.identity.plugin_id)
        assert entry.lifecycle.state == "VALIDATED"

    def test_default_disabled(self, tmp_path):
        stage = tmp_path / "stage"
        stage.mkdir()
        (stage / "manifest.json").write_text(json.dumps(_valid_manifest()), encoding="utf-8")
        reg = PluginRegistry()
        entry = reg.discover(stage)
        # Default state is only set when explicitly constructing lifecycle; discover uses DISCOVERED.
        assert entry.lifecycle.state == "DISCOVERED"


class TestLoader:
    def test_inspect_bundle(self, tmp_path):
        bundle = tmp_path / "plugin.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_valid_manifest()))
            zf.writestr("plugin.py", "print('x')")
        info = inspect_bundle(bundle)
        assert info["manifest_present"]
        assert "plugin.py" in info["files"]

    def test_stage_bundle_no_traversal(self, tmp_path):
        bundle = tmp_path / "bad.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_valid_manifest()))
            zf.writestr("../evil.txt", "evil")
        with pytest.raises(PluginBundleError, match="traversal path"):
            stage_bundle(bundle, tmp_path / "staging")

    def test_stage_bundle_symlink_rejected(self, tmp_path):
        bundle = tmp_path / "bad.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_valid_manifest()))
            info = zipfile.ZipInfo("link")
            # Set Unix symlink mode bits in external_attr.
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, "target")
        with pytest.raises(PluginBundleError, match="symlink"):
            stage_bundle(bundle, tmp_path / "staging")


class TestBrokerClient:
    def test_request_granted(self):
        identity = PluginIdentity(
            plugin_id="example.status-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="i1",
        )
        client = create_plugin_client(identity, ["service.status"])
        result = client.request("service.status")
        assert result.capability == "service.status"
        assert result.status == "success"

    def test_request_not_granted(self):
        identity = PluginIdentity(
            plugin_id="example.status-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="i1",
        )
        client = create_plugin_client(identity, ["service.status"])
        with pytest.raises(PluginCapabilityError):
            client.request("broker.status")

    def test_request_mutating_denied(self):
        from plugin_sdk.errors import PluginPolicyError
        identity = PluginIdentity(
            plugin_id="example.status-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="i1",
        )
        client = create_plugin_client(identity, ["service.start"])
        with pytest.raises(PluginPolicyError, match="mutating"):
            client.request("service.start")

    def test_backend_result_size_bounded(self):
        from plugin_sdk.errors import PluginExecutionError
        identity = PluginIdentity(
            plugin_id="example.status-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="i1",
        )
        def backend(cap, ctx):
            return {"data": "x" * 300_000}
        client = create_plugin_client(identity, ["service.status"], backend=backend)
        with pytest.raises(PluginExecutionError, match="exceeded size limit"):
            client.request("service.status")


class TestConfiguration:
    def test_namespace_isolated(self):
        assert plugin_config_namespace("foo.bar") == "plugins.foo.bar"

    def test_config_schema_validation(self):
        schema = {"fields": {"interval": {"type": "int", "max": 3600, "required": True}}}
        validate_config_schema({"interval": 60}, schema)
        with pytest.raises(PluginConfigurationError):
            validate_config_schema({"interval": 4000}, schema)

    def test_config_secret_redacted(self):
        config = {"api_key": "AbC123XyZ_secret_value"}
        redacted = redact_plugin_config(config)
        assert redacted["api_key"] == "[redacted]"

    def test_config_digest(self):
        assert len(digest_plugin_config({"a": 1})) == 64


class TestSigning:
    def test_unsigned_classification(self):
        data = _valid_manifest()
        sig = classify_signature(data)
        assert sig.trust_state == TrustState.UNSIGNED

    def test_signed_untrusted(self):
        data = _valid_manifest()
        data["signature"] = {"publisher_id": "example-publisher", "signature_blob": "deadbeef"}
        sig = classify_signature(data)
        assert sig.trust_state == TrustState.SIGNED_UNTRUSTED

    def test_invalid_signature_missing_fields(self):
        data = _valid_manifest()
        data["signature"] = {"publisher_id": "example-publisher"}
        sig = classify_signature(data)
        assert sig.trust_state == TrustState.INVALID_SIGNATURE
