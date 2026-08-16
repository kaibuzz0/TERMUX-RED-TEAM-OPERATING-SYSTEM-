from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from release_engine import candidate_gate
from release_engine.errors import BuildError


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unsigned_metadata() -> dict:
    return {
        "schema_version": 1,
        "release": {
            "release_id": "hive-os-1.1.0-rc.2-rc2-deadbeef0000",
            "version": "1.1.0-rc.2",
            "release_sequence": 22,
            "security_sequence": 22,
            "channel": "rc",
            "build_id": "rc2-deadbeef0000",
            "source_revision": "deadbeef" * 5,
            "commit": "deadbeef" * 5,
            "created_at": "2026-08-16T00:00:00Z",
            "minimum_supported_version": "0.0.0",
            "platforms": ["termux"],
            "architectures": ["aarch64"],
        },
        "manifest_digest": "a" * 64,
        "signing": {"algorithm": "Ed25519", "key_id": "", "signature": ""},
        "revocation": {"sequence": 0},
    }


def _candidate() -> dict:
    return {
        "status": "unsigned_candidate_only",
        "version": "1.1.0-rc.2",
        "rc1_sequence": 21,
        "security_sequence": 22,
        "source_revision": "deadbeef" * 5,
        "expected_production_key_id": "hive-release-prod-2026-02",
        "bundle": "candidate.tar.gz",
        "metadata": "candidate.metadata.json",
        "manifest": "candidate.manifest.json",
    }


def test_verify_candidate_hashes_accepts_portable_basename_entries(tmp_path: Path) -> None:
    artifact = tmp_path / "candidate.tar.gz"
    artifact.write_bytes(b"candidate")
    (tmp_path / "SHA256SUMS").write_text(
        f"{_sha256(artifact)}  {artifact.name}\n", encoding="utf-8"
    )

    result = candidate_gate.verify_candidate_hashes(tmp_path)

    assert result == {artifact.name: _sha256(artifact)}


def test_verify_candidate_hashes_rejects_tampered_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "candidate.tar.gz"
    artifact.write_bytes(b"candidate")
    original = _sha256(artifact)
    (tmp_path / "SHA256SUMS").write_text(f"{original}  {artifact.name}\n", encoding="utf-8")
    artifact.write_bytes(b"tampered")

    with pytest.raises(BuildError, match="candidate hash mismatch"):
        candidate_gate.verify_candidate_hashes(tmp_path)


def test_verify_candidate_hashes_rejects_nonportable_path(tmp_path: Path) -> None:
    artifact = tmp_path / "candidate.tar.gz"
    artifact.write_bytes(b"candidate")
    (tmp_path / "SHA256SUMS").write_text(
        f"{_sha256(artifact)}  /tmp/{artifact.name}\n", encoding="utf-8"
    )

    with pytest.raises(BuildError, match="basename-only"):
        candidate_gate.verify_candidate_hashes(tmp_path)


def test_validate_signed_metadata_accepts_exact_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    unsigned = _unsigned_metadata()
    signed = json.loads(json.dumps(unsigned))
    signed["signing"] = {
        "algorithm": "Ed25519",
        "key_id": "hive-release-prod-2026-02",
        "signature": "test-signature",
    }
    monkeypatch.setattr(candidate_gate, "verify_metadata", lambda metadata: None)

    candidate_gate.validate_signed_metadata(_candidate(), unsigned, signed)


def test_validate_signed_metadata_rejects_unsigned_field_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsigned = _unsigned_metadata()
    signed = json.loads(json.dumps(unsigned))
    signed["release"]["commit"] = "cafebabe" * 5
    signed["signing"] = {
        "algorithm": "Ed25519",
        "key_id": "hive-release-prod-2026-02",
        "signature": "test-signature",
    }
    monkeypatch.setattr(candidate_gate, "verify_metadata", lambda metadata: None)

    with pytest.raises(BuildError, match="does not belong to the exact unsigned candidate"):
        candidate_gate.validate_signed_metadata(_candidate(), unsigned, signed)


def test_validate_signed_metadata_rejects_wrong_signing_key() -> None:
    unsigned = _unsigned_metadata()
    signed = json.loads(json.dumps(unsigned))
    signed["signing"] = {
        "algorithm": "Ed25519",
        "key_id": "hive-parity-test-2026-01",
        "signature": "test-signature",
    }

    with pytest.raises(BuildError, match="must use production key"):
        candidate_gate.validate_signed_metadata(_candidate(), unsigned, signed)
