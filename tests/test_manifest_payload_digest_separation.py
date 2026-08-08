"""Verify manifest digest cannot substitute for payload (per-file) digest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from release_engine.manifest import build_release_manifest, manifest_digest
from release_engine.reproducibility import compute_bundle_digest
from release_engine.signing import sign_release_metadata
from release_engine.verifier import verify_release_bundle
from updates.errors import BundleError
from updates.manifest import build_manifest, _sha256, verify_manifest
from updates.trust import TrustStore


def _gen_key_pair() -> tuple:
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    return private, pem


def _write_trust(tmp_path, keys):
    lines = []
    for key_id, pem in keys.items():
        lines.append(f"# key_id: {key_id}")
        lines.append(pem)
    path = tmp_path / "trust.pem"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@pytest.fixture
def key_pair():
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    return private, pem


@pytest.fixture
def trust_store(tmp_path, key_pair):
    private, pem = key_pair
    trust = TrustStore.from_pem_file(_write_trust(tmp_path, {"test-key": pem}))
    trust._private_for_test = private
    return trust


def test_manifest_digest_not_accepted_as_file_digest(tmp_path):
    """
    A manifest digest (hash of canonical JSON entries) must not be accepted
    as a per-file payload digest by verify_manifest.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("hello")
    (src / "file2.txt").write_text("world")

    entries = build_manifest(src)
    md = manifest_digest(entries)

    # Tamper: replace file1's sha256 with the manifest digest
    entries[0]["sha256"] = md

    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    for entry in entries:
        rel = Path(entry["path"])
        (bundle_root / rel.parent).mkdir(parents=True, exist_ok=True)
        (bundle_root / rel).write_bytes((src / rel).read_bytes())

    # verify_manifest checks per-file sha256 against actual file content
    with pytest.raises(BundleError) as exc:
        verify_manifest(entries, bundle_root)
    assert "Digest mismatch" in str(exc.value)


def test_file_digest_not_accepted_as_manifest_digest(tmp_path, trust_store):
    """
    A per-file payload digest must not be accepted as the top-level
    manifest_digest in signed metadata.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("hello")

    entries = build_manifest(src)
    md = manifest_digest(entries)

    # Build a real signed release bundle
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(entries, indent=2, sort_keys=False))

    # Compute per-file digest of one file
    file_digest = _sha256(src / "file1.txt")

    # Create metadata with manifest_digest replaced by file digest
    metadata = {
        "schema_version": 1,
        "release_id": "test-001",
        "sequence": 1,
        "manifest_digest": file_digest,  # substituted!
        "platform": "android",
        "architecture": "arm64-v8a",
        "published_at": "2026-01-01T00:00:00Z",
    }
    signed = sign_release_metadata(metadata, trust_store._private_for_test, "test-key", file_digest)
    (bundle_dir / "metadata.json").write_text(json.dumps(signed, indent=2, sort_keys=False))

    import tarfile
    bundle_tar = tmp_path / "bundle.tar.gz"
    with tarfile.open(bundle_tar, "w:gz") as tar:
        tar.add(manifest_path, arcname="manifest.json")
        tar.add(bundle_dir / "metadata.json", arcname="metadata.json")

    work_dir = tmp_path / "work"
    with pytest.raises(Exception) as exc:
        verify_release_bundle(bundle_tar, work_dir, trust_store)
    assert "manifest digest mismatch" in str(exc.value).lower()


def test_structural_difference_prevents_digest_reuse(tmp_path):
    """
    The canonical input to manifest_digest is a JSON list of entries.
    The input to a file digest is raw binary bytes. They are structurally
    different and produce different digests.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("hello")

    entries = build_manifest(src)
    md = manifest_digest(entries)

    file_bytes = (src / "file1.txt").read_bytes()
    file_digest = hashlib.sha256(file_bytes).hexdigest()

    # Manifest digest canonical input
    canonical_input = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    assert md == hashlib.sha256(canonical_input).hexdigest()

    # File bytes are NOT the same as canonical manifest JSON bytes
    assert canonical_input != file_bytes
    assert md != file_digest


def test_verify_manifest_checks_per_file_not_manifest(tmp_path):
    """
    verify_manifest validates per-file hashes, not the manifest_digest.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("hello")

    entries = build_manifest(src)

    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    for entry in entries:
        rel = Path(entry["path"])
        (bundle_root / rel.parent).mkdir(parents=True, exist_ok=True)
        (bundle_root / rel).write_bytes((src / rel).read_bytes())

    # verify_manifest succeeds with correct per-file hashes
    verify_manifest(entries, bundle_root)

    # verify_manifest does not compute or check manifest_digest
    # (that happens in verify_release_bundle via metadata)


def test_bundle_digest_is_neither_manifest_nor_file(tmp_path, trust_store):
    """
    compute_bundle_digest produces a third distinct digest from tar.gz bytes,
    different from both manifest_digest and per-file payload digests.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.txt").write_text("hello")

    entries = build_manifest(src)
    md = manifest_digest(entries)
    file_digest = _sha256(src / "file1.txt")

    # Build a real bundle tar.gz
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text(json.dumps(entries, indent=2, sort_keys=False))

    import tarfile
    bundle_tar = tmp_path / "bundle.tar.gz"
    with tarfile.open(bundle_tar, "w:gz") as tar:
        tar.add(bundle_dir / "manifest.json", arcname="manifest.json")

    bundle_digest = compute_bundle_digest(bundle_tar)

    # All three are different
    assert bundle_digest != md
    assert bundle_digest != file_digest
    assert md != file_digest
