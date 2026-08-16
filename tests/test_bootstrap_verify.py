from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from bootstrap import verify_bundle as bootstrap


def _write_signed_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    raw = public.public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(bootstrap, "ROOT_KEY_PEM", public.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    monkeypatch.setattr(bootstrap, "ROOT_KEY_FINGERPRINT", hashlib.sha256(raw).hexdigest())

    payload = b"#!/usr/bin/env python3\nprint('hive')\n"
    manifest = [
        {
            "path": "bin/hive",
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "executable": True,
            "type": "required",
        }
    ]
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=False).encode("utf-8")
    metadata = {
        "schema_version": 1,
        "release": {
            "version": "2.0.0-rc.1",
            "release_id": "hive-os-2.0.0-rc.1-test",
            "commit": "a" * 40,
            "created_at": "2026-08-16T00:00:00+00:00",
            "minimum_hive_version": "0.0.0",
            "maximum_hive_version": None,
            "platforms": ["termux"],
            "architectures": ["aarch64"],
            "security_sequence": 21,
        },
        "artifacts": [],
        "manifest_digest": hashlib.sha256(manifest_bytes).hexdigest(),
        "signing": {"algorithm": "Ed25519", "key_id": bootstrap.ROOT_KEY_ID, "signature": ""},
        "revocation": {"sequence": 0},
    }
    signature = private.sign(bootstrap._canonical_json(metadata))
    metadata["signing"]["signature"] = base64.urlsafe_b64encode(signature).decode("ascii")
    metadata_bytes = json.dumps(metadata, indent=2).encode("utf-8")

    bundle = tmp_path / "release.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        for name, data in (
            ("metadata.json", metadata_bytes),
            ("manifest.json", manifest_bytes),
            ("bin/hive", payload),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return bundle


def test_clean_bootstrap_verifies_signed_release(tmp_path, monkeypatch):
    bundle = _write_signed_bundle(tmp_path, monkeypatch)
    extracted = tmp_path / "extracted"
    result = bootstrap.verify_bundle(bundle, extracted, "termux", "aarch64", current_sequence=20)
    assert result["verified"] is True
    assert result["version"] == "2.0.0-rc.1"
    assert result["security_sequence"] == 21
    assert (extracted / "bin" / "hive").is_file()


def test_bootstrap_rejects_rollback_sequence(tmp_path, monkeypatch):
    bundle = _write_signed_bundle(tmp_path, monkeypatch)
    with pytest.raises(bootstrap.BootstrapVerificationError, match="older than current"):
        bootstrap.verify_bundle(bundle, tmp_path / "extracted", "termux", "aarch64", current_sequence=22)


def test_bootstrap_rejects_path_traversal(tmp_path):
    bundle = tmp_path / "evil.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        data = b"owned"
        info = tarfile.TarInfo("../outside")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    with pytest.raises(bootstrap.BootstrapVerificationError, match="unsafe archive"):
        bootstrap.safe_extract(bundle, tmp_path / "extract")
    assert not (tmp_path / "outside").exists()


def test_bootstrap_rejects_symlink_member(tmp_path):
    bundle = tmp_path / "evil-link.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        archive.addfile(info)
    with pytest.raises(bootstrap.BootstrapVerificationError, match="unsafe archive member type"):
        bootstrap.safe_extract(bundle, tmp_path / "extract")
