"""Contract tests between the release engine and clean-install bootstrap."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from bootstrap import verify_bundle as bootstrap_verify
from release_engine.builder import build_release, seal_release_bundle
from release_engine.errors import BuildError
from release_engine.signing import sign_release_metadata


def _build_candidate(tmp_path: Path):
    source = tmp_path / "runtime"
    (source / "bin").mkdir(parents=True)
    hive = source / "bin" / "hive"
    hive.write_text("#!/usr/bin/env python3\nprint('hive contract test')\n", encoding="utf-8")
    hive.chmod(0o755)

    output = tmp_path / "release"
    result = build_release(
        source_dir=source,
        output_dir=output,
        version="2.0.0-rc.2",
        release_sequence=7,
        build_id="contract",
        source_revision="deadbeef",
        platforms=["termux"],
        architectures=["aarch64"],
        channel="rc",
    )
    metadata_path = output / f"{result['release_id']}.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return result, metadata


def _install_test_root(monkeypatch: pytest.MonkeyPatch, private_key: Ed25519PrivateKey, key_id: str) -> None:
    public = private_key.public_key()
    pem = public.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    raw = public.public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(bootstrap_verify, "ROOT_KEY_ID", key_id)
    monkeypatch.setattr(bootstrap_verify, "ROOT_KEY_PEM", pem)
    monkeypatch.setattr(bootstrap_verify, "ROOT_KEY_FINGERPRINT", hashlib.sha256(raw).hexdigest())


def test_release_builder_emits_clean_bootstrap_sequence_contract(tmp_path):
    result, metadata = _build_candidate(tmp_path)
    release = metadata["release"]

    assert release["release_sequence"] == 7
    assert release["security_sequence"] == 7
    assert release["source_revision"] == "deadbeef"
    assert release["commit"] == "deadbeef"
    assert result["metadata"]["release"]["security_sequence"] == 7


def test_sealed_release_bundle_is_accepted_by_clean_bootstrap(tmp_path, monkeypatch):
    result, metadata = _build_candidate(tmp_path)
    private_key = Ed25519PrivateKey.generate()
    key_id = "test-release-root"
    signed = sign_release_metadata(metadata, private_key, key_id, metadata["manifest_digest"])

    sealed = tmp_path / "hive-os-2.0.0-rc.2-contract.signed.tar.gz"
    sealed_result = seal_release_bundle(result["bundle_path"], signed, sealed)

    assert sealed_result["sealed"] is True
    assert sealed_result["release_id"] == result["release_id"]
    assert sealed_result["key_id"] == key_id

    _install_test_root(monkeypatch, private_key, key_id)
    verification = bootstrap_verify.verify_bundle(
        sealed,
        tmp_path / "verified",
        platform="termux",
        architecture="aarch64",
        current_sequence=6,
    )

    assert verification["verified"] is True
    assert verification["release_id"] == result["release_id"]
    assert verification["version"] == "2.0.0-rc.2"
    assert verification["security_sequence"] == 7
    assert verification["commit"] == "deadbeef"


def test_sealer_rejects_metadata_for_different_bundle_identity(tmp_path):
    result, metadata = _build_candidate(tmp_path)
    private_key = Ed25519PrivateKey.generate()
    signed = sign_release_metadata(metadata, private_key, "test-release-root", metadata["manifest_digest"])

    tampered = dict(signed)
    tampered_release = dict(signed["release"])
    tampered_release["version"] = "9.9.9"
    tampered["release"] = tampered_release

    with pytest.raises(BuildError, match="changes unsigned bundle metadata"):
        seal_release_bundle(result["bundle_path"], tampered, tmp_path / "must-not-exist.tar.gz")


def test_sealer_rejects_manifest_mismatch(tmp_path):
    result, metadata = _build_candidate(tmp_path)
    private_key = Ed25519PrivateKey.generate()
    signed = sign_release_metadata(metadata, private_key, "test-release-root", metadata["manifest_digest"])
    mismatched = dict(signed)
    mismatched["manifest_digest"] = "0" * 64

    with pytest.raises(BuildError, match="manifest digest does not match"):
        seal_release_bundle(result["bundle_path"], mismatched, tmp_path / "must-not-exist.tar.gz")
