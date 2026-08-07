"""Core Plugin SDK tests: manifest, identity, capabilities, compatibility."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from plugin_sdk import manifest_digest, load_manifest, SDK_VERSION, SCHEMA_VERSION
from plugin_sdk.capabilities import (
    MUTATING_CAPABILITIES,
    TYPE_ALLOWED_CAPABILITIES,
    classify_capability,
    validate_capability_set,
)
from plugin_sdk.compatibility import RuntimeVersions, negotiate_compatibility
from plugin_sdk.errors import (
    PluginCapabilityError,
    PluginCompatibilityError,
    PluginIdentityError,
    PluginManifestError,
)
from plugin_sdk.identity import PluginIdentity, digest_capability_grant, digest_configuration, verify_identity_binding


def _valid_manifest(extra: dict | None = None) -> dict:
    base = {
        "schema_version": SCHEMA_VERSION,
        "plugin": {
            "id": "example.status-plugin",
            "name": "Example Status Plugin",
            "version": "1.0.0",
            "sdk_version": SDK_VERSION,
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
        "lifecycle": {
            "auto_start": False,
        },
    }
    if extra:
        base.update(extra)
    return base


class TestManifestValidation:
    def test_valid_manifest(self):
        text = json.dumps(_valid_manifest())
        result = load_manifest(text)
        assert result["plugin"]["id"] == "example.status-plugin"
        assert result["plugin"]["type"] == "client"
        assert result["permissions"]["network"] == "deny"
        assert result["lifecycle"]["auto_start"] is False

    def test_unknown_schema_version_fails_closed(self):
        data = _valid_manifest()
        data["schema_version"] = 99
        with pytest.raises(PluginManifestError, match="unsupported schema_version"):
            load_manifest(json.dumps(data))

    def test_duplicate_keys_rejected(self):
        raw = json.dumps(_valid_manifest())
        # Insert a duplicate "version" inside the plugin object.
        dup = raw.replace('"plugin": {', '"plugin": {"version": "2.0.0", ', 1)
        with pytest.raises(PluginManifestError, match="duplicate key"):
            load_manifest(dup)

    def test_unknown_top_level_field(self):
        data = _valid_manifest()
        data["backdoor"] = True
        with pytest.raises(PluginManifestError, match="unknown top-level fields"):
            load_manifest(json.dumps(data))

    def test_invalid_plugin_id(self):
        data = _valid_manifest()
        data["plugin"]["id"] = "0starts.with.number"
        with pytest.raises(PluginManifestError, match="plugin.id format"):
            load_manifest(json.dumps(data))

    def test_invalid_version(self):
        data = _valid_manifest()
        data["plugin"]["version"] = "not-semver"
        with pytest.raises(PluginManifestError, match="must be semantic version"):
            load_manifest(json.dumps(data))

    def test_unknown_plugin_type(self):
        data = _valid_manifest()
        data["plugin"]["type"] = "shell"
        with pytest.raises(PluginManifestError, match="unsupported plugin type"):
            load_manifest(json.dumps(data))

    def test_wildcard_capability_rejected(self):
        data = _valid_manifest()
        data["permissions"]["requested_capabilities"] = ["service.*"]
        with pytest.raises(PluginManifestError, match="wildcard"):
            load_manifest(json.dumps(data))

    def test_shell_capability_rejected(self):
        data = _valid_manifest()
        data["permissions"]["requested_capabilities"] = ["shell"]
        with pytest.raises(PluginManifestError, match="forbidden"):
            load_manifest(json.dumps(data))

    def test_auto_start_default_false(self):
        data = _valid_manifest()
        del data["lifecycle"]["auto_start"]
        result = load_manifest(json.dumps(data))
        assert result["lifecycle"]["auto_start"] is False

    def test_network_default_deny(self):
        data = _valid_manifest()
        del data["permissions"]["network"]
        result = load_manifest(json.dumps(data))
        assert result["permissions"]["network"] == "deny"

    def test_arbitrary_filesystem_rejected(self):
        data = _valid_manifest()
        data["permissions"]["filesystem"] = ["/etc/passwd"]
        with pytest.raises(PluginManifestError, match="absolute path"):
            load_manifest(json.dumps(data))

    def test_secret_permission_rejected(self):
        data = _valid_manifest()
        data["permissions"]["secrets"] = ["API_KEY"]
        with pytest.raises(PluginManifestError, match="secrets must be empty"):
            load_manifest(json.dumps(data))

    def test_manifest_from_path(self, tmp_path):
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
        result = load_manifest(path)
        assert result["plugin"]["id"] == "example.status-plugin"


class TestIdentity:
    def test_stable_identity_from_manifest(self):
        data = _valid_manifest()
        digest = manifest_digest(json.dumps(data))
        identity = PluginIdentity.from_manifest(data, digest)
        assert identity.plugin_id == "example.status-plugin"
        assert identity.plugin_version == "1.0.0"
        assert identity.manifest_digest == digest
        assert identity.actor_id().startswith("plugin:example.status-plugin:")

    def test_digest_mismatch_rejected(self):
        data = _valid_manifest()
        identity = PluginIdentity.from_manifest(data, "wrong")
        with pytest.raises(PluginIdentityError, match="manifest_digest mismatch"):
            verify_identity_binding(identity, data, manifest_digest(json.dumps(data)))

    def test_capability_grant_digest(self):
        digest = digest_capability_grant("example.status-plugin", ["service.status"], "observer", "ALLOW")
        assert len(digest) == 64
        digest2 = digest_capability_grant("example.status-plugin", ["service.status"], "observer", "ALLOW")
        assert digest == digest2

    def test_configuration_digest(self):
        digest = digest_configuration({"a": 1, "b": [2, 3]})
        assert len(digest) == 64


class TestCapabilities:
    def test_requested_subset(self):
        granted = validate_capability_set(
            requested=["service.status", "broker.status"],
            broker_advertised={"service.status", "broker.status", "service.list"},
            profile_allowed=set(TYPE_ALLOWED_CAPABILITIES["client"]),
            plugin_type="client",
        )
        assert sorted(granted) == ["broker.status", "service.status"]

    def test_missing_broker_capability(self):
        with pytest.raises(PluginCapabilityError, match="not advertised by broker"):
            validate_capability_set(
                requested=["service.status"],
                broker_advertised=set(),
                profile_allowed=set(TYPE_ALLOWED_CAPABILITIES["client"]),
                plugin_type="client",
            )

    def test_policy_denial(self):
        with pytest.raises(PluginCapabilityError, match="denied by profile"):
            validate_capability_set(
                requested=["service.status"],
                broker_advertised={"service.status"},
                profile_allowed=set(),
                plugin_type="client",
            )

    def test_read_only_grant(self):
        granted = validate_capability_set(
            requested=["service.status"],
            broker_advertised={"service.status"},
            profile_allowed={"service.status"},
            plugin_type="client",
        )
        assert granted == ["service.status"]

    def test_mutation_denied(self):
        from plugin_sdk import capabilities as caps
        original = dict(caps.TYPE_ALLOWED_CAPABILITIES)
        try:
            caps.TYPE_ALLOWED_CAPABILITIES["validator"] = frozenset({"service.start"})
            with pytest.raises(PluginCapabilityError, match="mutating capabilities denied"):
                validate_capability_set(
                    requested=["service.start"],
                    broker_advertised={"service.start"},
                    profile_allowed={"service.start"},
                    plugin_type="validator",
                )
        finally:
            caps.TYPE_ALLOWED_CAPABILITIES.clear()
            caps.TYPE_ALLOWED_CAPABILITIES.update(original)

    def test_plugin_self_grant_denied(self):
        with pytest.raises(PluginCapabilityError, match="not allowed for plugin type"):
            validate_capability_set(
                requested=["broker.policy.modify"],
                broker_advertised={"broker.policy.modify"},
                profile_allowed={"broker.policy.modify"},
                plugin_type="client",
            )

    def test_classify_capability(self):
        assert classify_capability("service.status") == "read-only"
        assert classify_capability("service.start") == "mutating"


class TestCompatibility:
    def test_incompatible_major_version_fails(self):
        data = _valid_manifest()
        data["plugin"]["sdk_version"] = "2.0.0"
        with pytest.raises(PluginCompatibilityError, match="incompatible SDK version"):
            negotiate_compatibility(data, {"service.status", "broker.status"})

    def test_missing_capability_fails(self):
        data = _valid_manifest()
        data["compatibility"]["required_capabilities"] = ["missing.capability"]
        with pytest.raises(PluginCompatibilityError, match="required capabilities missing"):
            negotiate_compatibility(data, {"service.status", "broker.status"})

    def test_compatible(self):
        data = _valid_manifest()
        negotiate_compatibility(data, {"service.status", "broker.status"})
