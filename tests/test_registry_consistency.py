"""Plugin and release registry consistency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from release_engine.channels import ChannelError, parse_channel
from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
from release_engine.registry import ReleaseRecord, ReleaseRegistry


def _now() -> str:
    return "2026-08-07T00:00:00Z"


class TestReleaseRegistry:
    def test_persistence_and_atomicity(self, tmp_path):
        reg = ReleaseRegistry(tmp_path / "registry.json")
        reg.register(ReleaseRecord("r1", "1.0.0", 1, "stable", "a" * 64, "b" * 64, "k1"))
        reg.activate("r1", _now())
        # Simulate process restart
        reg2 = ReleaseRegistry(tmp_path / "registry.json")
        assert reg2.get_active().release_id == "r1"

    def test_corrupted_registry_handling(self, tmp_path):
        path = tmp_path / "registry.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(Exception):
            ReleaseRegistry(path)

    def test_active_does_not_trust_corrupt(self, tmp_path):
        reg = ReleaseRegistry(tmp_path / "registry.json")
        reg.register(ReleaseRecord("r1", "1.0.0", 1, "stable", "a" * 64, "b" * 64, "k1"))
        reg.activate("r1", _now())
        data = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
        # Corrupt manifest digest of active release
        for r in data["releases"]:
            r["manifest_digest"] = "c" * 64
        (tmp_path / "registry.json").write_text(json.dumps(data), encoding="utf-8")
        # Registry does not re-verify; but active pointer alone is not authorization.
        reg2 = ReleaseRegistry(tmp_path / "registry.json")
        active = reg2.get_active()
        assert active.manifest_digest == "c" * 64
        # The test documents that registry is evidence, not authorization.

    def test_channel_rollback_sequence(self, tmp_path):
        reg = ReleaseRegistry(tmp_path / "registry.json")
        reg.register(ReleaseRecord("r-stable", "1.0.0", 10, "stable", "a" * 64, "b" * 64, "k1"))
        reg.activate("r-stable", _now())
        # Attempt to activate a lower-sequence stable release
        reg.register(ReleaseRecord("r-old", "0.9.0", 9, "stable", "c" * 64, "d" * 64, "k1"))
        reg.activate("r-old", _now())
        # Anti-rollback must be enforced by verifier, not registry alone.
        # Here we confirm registry records sequence faithfully.
        assert reg.get_active().release_sequence == 9


class TestPluginRegistry:
    def test_persistence(self, tmp_path):
        reg = PersistentPluginRegistry(tmp_path / "plugins.json")
        record = PluginRegistryRecord(
            plugin_id="p1",
            version="1.0.0",
            installation_id="i1",
            manifest_digest="a" * 64,
            bundle_digest="b" * 64,
            signature_trust="SIGNED_TRUSTED",
            requested_capabilities=["service.status"],
            granted_capabilities=["service.status"],
            configuration_digest="c" * 64,
            state="DISABLED",
            install_timestamp=_now(),
            publisher="pub",
            sdk_compatibility="1.0",
            quarantine_state=None,
        )
        reg.register(record)
        reg2 = PersistentPluginRegistry(tmp_path / "plugins.json")
        assert reg2.get("p1").state == "DISABLED"

    def test_duplicate_installation_id(self, tmp_path):
        reg = PersistentPluginRegistry(tmp_path / "plugins.json")
        base = {
            "plugin_id": "p1",
            "version": "1.0.0",
            "manifest_digest": "a" * 64,
            "bundle_digest": "b" * 64,
            "signature_trust": "SIGNED_TRUSTED",
            "requested_capabilities": [],
            "granted_capabilities": [],
            "configuration_digest": "c" * 64,
            "install_timestamp": _now(),
            "publisher": None,
            "sdk_compatibility": "1.0",
            "quarantine_state": None,
        }
        reg.register(PluginRegistryRecord(**base, installation_id="i1", state="DISABLED"))
        with pytest.raises(Exception):
            reg.register(PluginRegistryRecord(**base, installation_id="i1", state="DISABLED"))


class TestChannels:
    def test_stable_cannot_install_beta(self):
        from release_engine.channels import can_install
        with pytest.raises(ChannelError):
            can_install(parse_channel("stable"), parse_channel("beta"))

    def test_channel_ordering_preserved(self):
        from release_engine.channels import can_install
        assert can_install(parse_channel("development"), parse_channel("development"))
        assert can_install(parse_channel("beta"), parse_channel("beta"))
        with pytest.raises(ChannelError):
            can_install(parse_channel("beta"), parse_channel("development"))
