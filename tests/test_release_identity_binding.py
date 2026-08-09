"""Signed release identity binding and trust-store regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from release_engine.builder import build_release
from release_engine.errors import ReleaseFormatError
from release_engine.signing import load_private_key, sign_release_metadata, verify_release_metadata
from release_engine.verifier import verify_release_bundle
from updates.trust import TrustStore


def _gen_key_pair() -> tuple[Ed25519PrivateKey, str]:
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    return private, pem


def _sign_fixture(tmp_path: Path, metadata: dict, private: Ed25519PrivateKey, key_id: str) -> dict:
    signed = sign_release_metadata(metadata, private, key_id, metadata.get("manifest_digest", ""))
    return signed


def _write_trust(tmp_path: Path, keys: dict[str, str]) -> Path:
    lines = []
    for key_id, pem in keys.items():
        lines.append(f"# key_id: {key_id}")
        lines.append(pem)
    path = tmp_path / "trust.pem"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _build_and_sign(tmp_path: Path, private: Ed25519PrivateKey, key_id: str, version: str = "1.0.0", seq: int = 1, channel: str = "stable") -> tuple[Path, Path, dict]:
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    result = build_release(src, out, version, seq, "b1", "rev1", ["linux"], ["aarch64"], channel=channel)
    bundle = result["bundle_path"]
    signed = _sign_fixture(tmp_path, result["metadata"], private, key_id)
    metadata_path = out / f"{result['release_id']}.signed.json"
    metadata_path.write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
    # We also need to inject signed metadata into bundle for verification
    # For tests we verify bundle metadata separately.
    return bundle, metadata_path, signed


def test_valid_single_key(tmp_path):
    private, pem = _gen_key_pair()
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem}))
    bundle, _, signed = _build_and_sign(tmp_path, private, "k1")
    # Replace unsigned metadata in bundle with signed
    import tarfile
    work = tmp_path / "work"
    work.mkdir()
    with tarfile.open(bundle, "r:gz") as tar:
        tar.extractall(work)
    (work / "metadata.json").write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
    signed_bundle = tmp_path / "signed.tar.gz"
    with tarfile.open(signed_bundle, "w:gz") as tar:
        for f in sorted(work.rglob("*"), key=lambda p: str(p.relative_to(work))):
            if f.is_file():
                tar.add(f, arcname=f.relative_to(work).as_posix())
    verify_release_bundle(signed_bundle, tmp_path / "vwork", trust, current_sequence=0)


def test_multiple_keys_selects_correct(tmp_path):
    priv1, pem1 = _gen_key_pair()
    priv2, pem2 = _gen_key_pair()
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem1, "k2": pem2}))
    bundle, _, signed = _build_and_sign(tmp_path, priv2, "k2")
    _inject_signed(bundle, signed, tmp_path / "signed.tar.gz")
    verify_release_bundle(tmp_path / "signed.tar.gz", tmp_path / "vwork", trust, current_sequence=0)


def test_wrong_key_id_fails(tmp_path):
    private, pem = _gen_key_pair()
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem}))
    bundle, _, signed = _build_and_sign(tmp_path, private, "wrong")
    _inject_signed(bundle, signed, tmp_path / "signed.tar.gz")
    with pytest.raises(Exception):
        verify_release_bundle(tmp_path / "signed.tar.gz", tmp_path / "vwork", trust, current_sequence=0)


def test_tampered_version_fails(tmp_path):
    private, pem = _gen_key_pair()
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem}))
    bundle, _, signed = _build_and_sign(tmp_path, private, "k1")
    signed["release"]["version"] = "9.9.9"
    _inject_signed(bundle, signed, tmp_path / "signed.tar.gz")
    with pytest.raises(Exception):
        verify_release_bundle(tmp_path / "signed.tar.gz", tmp_path / "vwork", trust, current_sequence=0)


def test_tampered_manifest_digest_fails(tmp_path):
    private, pem = _gen_key_pair()
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem}))
    bundle, _, signed = _build_and_sign(tmp_path, private, "k1")
    signed["manifest_digest"] = "a" * 64
    _inject_signed(bundle, signed, tmp_path / "signed.tar.gz")
    with pytest.raises(Exception):
        verify_release_bundle(tmp_path / "signed.tar.gz", tmp_path / "vwork", trust, current_sequence=0)


def test_revoked_key_fails(tmp_path):
    private, pem = _gen_key_pair()
    store = TrustStore.from_pem_file(_write_trust(tmp_path, {"k1": pem}))
    store.keys["k1"].status = "revoked"
    bundle, _, signed = _build_and_sign(tmp_path, private, "k1")
    _inject_signed(bundle, signed, tmp_path / "signed.tar.gz")
    with pytest.raises(Exception):
        verify_release_bundle(tmp_path / "signed.tar.gz", tmp_path / "vwork", store, current_sequence=0)


def _inject_signed(bundle: Path, signed: dict, output: Path) -> None:
    import tarfile, json, tempfile
    work = Path(tempfile.mkdtemp())
    with tarfile.open(bundle, "r:gz") as tar:
        tar.extractall(work)
    (work / "metadata.json").write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
    with tarfile.open(output, "w:gz") as tar:
        for f in sorted(work.rglob("*"), key=lambda p: str(p.relative_to(work))):
            if f.is_file():
                tar.add(f, arcname=f.relative_to(work).as_posix())
