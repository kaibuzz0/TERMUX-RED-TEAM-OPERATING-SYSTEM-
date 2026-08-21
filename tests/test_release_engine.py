"""Release engine tests."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from release_engine.builder import build_release
from release_engine.channels import ReleaseChannel, can_install, parse_channel
from release_engine.dependencies import PluginDependency, detect_cycle, resolve_dependencies
from release_engine.errors import (
    BuildError,
    ChannelError,
    DependencyError,
    ManifestError,
    RegistryError,
    ReleaseFormatError,
    VersionError,
)
from release_engine.manifest import build_release_manifest, manifest_digest
from release_engine.plugin_package import create_plugin_package, verify_plugin_package
from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
from release_engine.registry import ReleaseRecord, ReleaseRegistry
from release_engine.reproducibility import ReproducibilityClass, compute_bundle_digest
from release_engine.sbom import SbomComponent, generate_sbom
from release_engine.signing import load_private_key, sign_release_metadata
from release_engine.version import parse_release_version


class TestVersion:
    def test_valid_version(self):
        v = parse_release_version("1.2.3")
        assert str(v) == "1.2.3"

    def test_prerelease(self):
        v = parse_release_version("1.0.0-alpha.1")
        assert v.prerelease == "alpha.1"

    def test_malformed(self):
        with pytest.raises(VersionError):
            parse_release_version("1.0")

    def test_compare(self):
        a = parse_release_version("1.0.0")
        b = parse_release_version("1.0.1")
        assert a.compare(b) < 0


class TestReproducibleBuild:
    def test_build_excludes_secrets_and_dev(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "bin").mkdir()
        (src / "bin" / "hive").write_text("#!/bin/sh\necho hi", encoding="utf-8")
        (src / ".env").write_text("KEY=secret", encoding="utf-8")
        (src / ".git").mkdir()
        (src / ".git" / "config").write_text("[core]", encoding="utf-8")

        out = tmp_path / "out"
        result = build_release(
            source_dir=src,
            output_dir=out,
            version="1.0.0",
            release_sequence=1,
            build_id="b1",
            source_revision="abc",
            platforms=["linux"],
            architectures=["aarch64"],
        )
        paths = {e["path"] for e in build_release_manifest(src)}
        assert "bin/hive" in paths
        assert ".env" not in paths
        assert ".git/config" not in paths
        assert result["classification"] == ReproducibilityClass.CONTENT_REPRODUCIBLE.value

    def test_repeated_build_digest(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "bin").mkdir()
        (src / "bin" / "hive").write_text("#!/bin/sh\necho hello", encoding="utf-8")
        (src / "hive-canonical.json").write_text('{"project": "Hive OS"}', encoding="utf-8")
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"
        build_release(src, out1, "1.0.0", 1, "b1", "abc", ["linux"], ["aarch64"])
        build_release(src, out2, "1.0.0", 1, "b1", "abc", ["linux"], ["aarch64"])
        d1 = compute_bundle_digest(out1 / "hive-os-1.0.0-b1.tar.gz")
        d2 = compute_bundle_digest(out2 / "hive-os-1.0.0-b1.tar.gz")
        assert d1 == d2

    def test_manifest_digest_changes_on_content(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "bin").mkdir()
        (src / "bin" / "hive").write_text("#!/bin/sh\necho a", encoding="utf-8")
        (src / "hive-canonical.json").write_text('{"project": "Hive OS"}', encoding="utf-8")
        m1 = manifest_digest(build_release_manifest(src))
        (src / "bin" / "hive").write_text("#!/bin/sh\necho b", encoding="utf-8")
        m2 = manifest_digest(build_release_manifest(src))
        assert m1 != m2


class TestChannels:
    def test_stable_cannot_install_beta(self):
        with pytest.raises(ChannelError):
            can_install(parse_channel("stable"), parse_channel("beta"))

    def test_beta_can_install_beta(self):
        assert can_install(parse_channel("beta"), parse_channel("beta"))

    def test_development_can_install_development(self):
        assert can_install(parse_channel("development"), parse_channel("development"))


class TestDependencies:
    def test_valid_resolution(self):
        resolved = resolve_dependencies(
            [{"plugin_id": "a", "min_version": "1.0.0"}],
            {"a": {"version": "1.2.0"}},
            hive_version="2.0.0",
            sdk_version="1.0.0",
        )
        assert resolved[0]["resolved_version"] == "1.2.0"

    def test_missing_required_dependency(self):
        with pytest.raises(DependencyError):
            resolve_dependencies(
                [{"plugin_id": "a", "required": True}],
                {},
                hive_version="2.0.0",
                sdk_version="1.0.0",
            )

    def test_version_conflict(self):
        with pytest.raises(DependencyError):
            resolve_dependencies(
                [{"plugin_id": "a", "max_version": "1.0.0"}],
                {"a": {"version": "2.0.0"}},
                hive_version="2.0.0",
                sdk_version="1.0.0",
            )

    def test_cycle_detection(self):
        cycle = detect_cycle({"a": ["b"], "b": ["c"], "c": ["a"]})
        assert cycle is not None
        assert "a" in cycle


class TestReleaseRegistry:
    def test_persistence(self, tmp_path):
        reg = ReleaseRegistry(tmp_path / "registry.json")
        record = ReleaseRecord(
            release_id="r1",
            version="1.0.0",
            release_sequence=1,
            channel="stable",
            manifest_digest="a" * 64,
            bundle_digest="b" * 64,
            signing_key_id="k1",
        )
        reg.register(record)
        reg2 = ReleaseRegistry(tmp_path / "registry.json")
        assert len(reg2.list_releases()) == 1

    def test_activate_and_rollback(self, tmp_path):
        reg = ReleaseRegistry(tmp_path / "registry.json")
        reg.register(ReleaseRecord("r1", "1.0.0", 1, "stable", "a" * 64, "b" * 64, "k1"))
        reg.activate("r1", "t1")
        assert reg.get_active().release_id == "r1"
        reg.register(ReleaseRecord("r2", "1.1.0", 2, "stable", "c" * 64, "d" * 64, "k1"))
        reg.activate("r2", "t2")
        eligible = reg.rollback_eligible()
        assert any(r.release_id == "r1" for r in eligible)


class TestPluginPackage:
    def test_create_package(self, tmp_path):
        plugin = tmp_path / "plugin"
        plugin.mkdir()
        manifest = {
            "schema_version": 1,
            "plugin": {
                "id": "example.test",
                "name": "Test Plugin",
                "version": "1.0.0",
                "sdk_version": "1.0",
                "entrypoint": "example.main",
                "type": "client",
            },
            "compatibility": {
                "minimum_hive_version": "1.0.0-dev",
                "required_broker_version": "1.0",
                "required_capabilities": ["service.status"],
            },
            "permissions": {
                "requested_capabilities": ["service.status"],
                "filesystem": [],
                "network": "deny",
                "secrets": [],
            },
            "lifecycle": {"auto_start": False},
        }
        (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        pkg = tmp_path / "plugin.hivepkg"
        info = create_plugin_package(plugin, pkg)
        assert info["plugin_id"] == "example.test"
        assert pkg.exists()


class TestSbom:
    def test_sbom(self):
        sbom = generate_sbom("1.0.0", "1.0", [SbomComponent("cryptography", "42.0.0")])
        assert sbom["release_version"] == "1.0.0"
        assert sbom["components"][0]["name"] == "cryptography"


class TestSigningAndTrust:
    def test_sign_and_verify(self, tmp_path):
        from updates.trust import TrustStore
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private = Ed25519PrivateKey.generate()
        public = private.public_key()
        pem = public.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
        (tmp_path / "trust.pem").write_text(f"# key_id: k1\n{pem}", encoding="utf-8")
        trust = TrustStore.from_pem_file(tmp_path / "trust.pem")

        metadata = {
            "schema_version": 1,
            "release": {"release_id": "r1", "version": "1.0.0", "release_sequence": 1},
            "manifest_digest": "a" * 64,
        }
        signed = sign_release_metadata(metadata, private, "k1", metadata["manifest_digest"])
        from release_engine.signing import verify_release_metadata
        verify_release_metadata(signed, trust)
