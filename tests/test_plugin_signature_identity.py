"""Plugin signature identity binding."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from plugin_sdk.manifest import load_manifest
from release_engine.plugin_package import create_plugin_package, sign_plugin_package, verify_plugin_package
from updates.trust import TrustStore


def _make_plugin(tmp_path: Path, plugin_id: str = "plugin.a", version: str = "1.0.0", requested: list[str] | None = None) -> Path:
    if requested is None:
        requested = ["service.status"]
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    manifest = {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": "Test Plugin",
            "version": version,
            "sdk_version": "1.0",
            "entrypoint": "plugin.main",
            "type": "client",
        },
        "compatibility": {
            "minimum_hive_version": "1.0.0-dev",
            "required_broker_version": "1.0",
            "required_capabilities": requested,
        },
        "permissions": {
            "requested_capabilities": requested,
            "filesystem": [],
            "network": "deny",
            "secrets": [],
        },
        "lifecycle": {"auto_start": False},
    }
    (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin / "main.py").write_text("def main(): pass", encoding="utf-8")
    return plugin


def _trust(tmp_path: Path, pem: str) -> TrustStore:
    path = tmp_path / "trust.pem"
    path.write_text(f"# key_id: pub\n{pem}", encoding="utf-8")
    return TrustStore.from_pem_file(path)


def test_plugin_signature_identity_binding(tmp_path):
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    trust = _trust(tmp_path, pem)

    plugin = _make_plugin(tmp_path, "plugin.a", "1.0.0")
    pkg = tmp_path / "plugin.hivepkg"
    info = create_plugin_package(plugin, pkg)

    metadata = {
        "plugin_id": "plugin.a",
        "version": "1.0.0",
        "manifest_digest": info["manifest_digest"],
        "bundle_digest": info["bundle_digest"],
        "publisher": "pub",
        "sdk_compatibility": "1.0",
    }
    signed = sign_plugin_package(metadata, private, "pub")
    # Write metadata into staged package before verification
    with zipfile.ZipFile(pkg, "a") as zf:
        zf.writestr("metadata.json", json.dumps(signed, indent=2, sort_keys=True))

    result = verify_plugin_package(pkg, tmp_path / "work", trust)
    assert result["plugin_id"] == "plugin.a"


def test_changed_plugin_id_fails(tmp_path):
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    trust = _trust(tmp_path, pem)
    plugin = _make_plugin(tmp_path, "plugin.a", "1.0.0")
    pkg = tmp_path / "plugin.hivepkg"
    create_plugin_package(plugin, pkg)

    metadata = {
        "plugin_id": "plugin.b",
        "version": "1.0.0",
        "manifest_digest": "a" * 64,
        "bundle_digest": "b" * 64,
        "publisher": "pub",
        "sdk_compatibility": "1.0",
    }
    signed = sign_plugin_package(metadata, private, "pub")
    with zipfile.ZipFile(pkg, "a") as zf:
        zf.writestr("metadata.json", json.dumps(signed, indent=2, sort_keys=True))
    with pytest.raises(Exception):
        verify_plugin_package(pkg, tmp_path / "work", trust)
