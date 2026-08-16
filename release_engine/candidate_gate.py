"""Post-signing gate for an offline Hive release candidate.

This module deliberately has no private-key handling. It consumes the unsigned
candidate kit emitted by CI plus an externally produced signed metadata JSON,
proves that the signature belongs to that exact candidate, seals the metadata
into the archive, and runs the clean-install bootstrap verifier before emitting
publishable artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from bootstrap.verify_bundle import verify_bundle, verify_metadata
from release_engine.builder import seal_release_bundle
from release_engine.errors import BuildError

RC1_RELEASE_ID = "hive-os-1.1.0-rc.1-20260815-parity"
RC1_SECURITY_SEQUENCE = 21
EXPECTED_VERSION = "1.1.0-rc.2"
EXPECTED_SECURITY_SEQUENCE = 22
EXPECTED_PLATFORM = "termux"
EXPECTED_ARCHITECTURE = "aarch64"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"invalid JSON file {path}: {exc}") from exc


def _unsigned_view(metadata: dict[str, Any]) -> dict[str, Any]:
    value = dict(metadata)
    value["signing"] = {"algorithm": "Ed25519", "key_id": "", "signature": ""}
    return value


def verify_candidate_hashes(candidate_dir: Path) -> dict[str, str]:
    sums_path = candidate_dir / "SHA256SUMS"
    if not sums_path.is_file():
        raise BuildError("candidate kit is missing SHA256SUMS")

    verified: dict[str, str] = {}
    for line_number, raw in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise BuildError(f"invalid SHA256SUMS line {line_number}")
        expected, name = parts[0], parts[1].strip()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise BuildError(f"invalid SHA-256 digest on line {line_number}")
        path = Path(name)
        if path.name != name or path.is_absolute() or name in {".", ".."}:
            raise BuildError(f"SHA256SUMS must contain basename-only paths: {name!r}")
        artifact = candidate_dir / name
        if not artifact.is_file():
            raise BuildError(f"candidate hash target is missing: {name}")
        actual = _sha256(artifact)
        if actual != expected:
            raise BuildError(f"candidate hash mismatch: {name}")
        if name in verified:
            raise BuildError(f"duplicate SHA256SUMS entry: {name}")
        verified[name] = actual

    if not verified:
        raise BuildError("candidate SHA256SUMS is empty")
    return verified


def validate_signed_metadata(
    candidate: dict[str, Any], unsigned_metadata: dict[str, Any], signed_metadata: dict[str, Any]
) -> None:
    if _unsigned_view(signed_metadata) != _unsigned_view(unsigned_metadata):
        raise BuildError("signed metadata does not belong to the exact unsigned candidate")

    signing = signed_metadata.get("signing")
    if not isinstance(signing, dict):
        raise BuildError("signed metadata is missing signing block")
    expected_key_id = candidate.get("expected_production_key_id")
    if signing.get("algorithm") != "Ed25519":
        raise BuildError("signed candidate must use Ed25519")
    if not isinstance(expected_key_id, str) or not expected_key_id:
        raise BuildError("candidate does not declare expected production key id")
    if signing.get("key_id") != expected_key_id:
        raise BuildError(
            f"signed candidate must use production key {expected_key_id}; got {signing.get('key_id')!r}"
        )
    if not isinstance(signing.get("signature"), str) or not signing["signature"]:
        raise BuildError("signed candidate has no signature")

    release = signed_metadata.get("release")
    if not isinstance(release, dict):
        raise BuildError("signed candidate is missing release metadata")
    if release.get("version") != EXPECTED_VERSION:
        raise BuildError(f"unexpected candidate version: {release.get('version')!r}")
    if release.get("security_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise BuildError("RC.2 security sequence must be exactly 22")
    if release.get("release_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise BuildError("RC.2 release sequence must be exactly 22")
    if release.get("platforms") != [EXPECTED_PLATFORM]:
        raise BuildError("RC.2 candidate platform contract mismatch")
    if release.get("architectures") != [EXPECTED_ARCHITECTURE]:
        raise BuildError("RC.2 candidate architecture contract mismatch")
    if release.get("commit") != candidate.get("source_revision"):
        raise BuildError("signed candidate commit does not match CANDIDATE.json")
    if release.get("source_revision") != candidate.get("source_revision"):
        raise BuildError("signed candidate source revision does not match CANDIDATE.json")
    if candidate.get("security_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise BuildError("CANDIDATE.json does not carry RC.2 sequence 22")
    if candidate.get("rc1_sequence") != RC1_SECURITY_SEQUENCE:
        raise BuildError("CANDIDATE.json RC.1 baseline is not sequence 21")

    # This checks the actual Ed25519 signature against the production root
    # embedded in the clean-install bootstrap.
    verify_metadata(signed_metadata)


def gate_candidate(candidate_dir: Path, signed_metadata_path: Path, output_dir: Path) -> dict[str, Any]:
    candidate_dir = candidate_dir.expanduser().resolve()
    signed_metadata_path = signed_metadata_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()

    if not candidate_dir.is_dir():
        raise BuildError(f"candidate directory not found: {candidate_dir}")
    hashes = verify_candidate_hashes(candidate_dir)

    candidate = _read_json(candidate_dir / "CANDIDATE.json")
    if not isinstance(candidate, dict):
        raise BuildError("CANDIDATE.json must be an object")
    if candidate.get("status") != "unsigned_candidate_only":
        raise BuildError("candidate kit status is not unsigned_candidate_only")

    bundle_name = candidate.get("bundle")
    metadata_name = candidate.get("metadata")
    manifest_name = candidate.get("manifest")
    for label, name in (("bundle", bundle_name), ("metadata", metadata_name), ("manifest", manifest_name)):
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise BuildError(f"candidate {label} name is unsafe")
        if name not in hashes:
            raise BuildError(f"candidate {label} is not covered by SHA256SUMS: {name}")

    unsigned_metadata = _read_json(candidate_dir / metadata_name)
    signed_metadata = _read_json(signed_metadata_path)
    if not isinstance(unsigned_metadata, dict) or not isinstance(signed_metadata, dict):
        raise BuildError("release metadata must be an object")
    validate_signed_metadata(candidate, unsigned_metadata, signed_metadata)

    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise BuildError("publishable output directory must be empty")

    release_id = signed_metadata["release"].get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise BuildError("signed candidate has no release id")
    sealed_bundle = output_dir / f"{release_id}.tar.gz"
    seal_result = seal_release_bundle(candidate_dir / bundle_name, signed_metadata, sealed_bundle)

    with tempfile.TemporaryDirectory(prefix="hive-rc2-gate-") as temp:
        bootstrap_result = verify_bundle(
            sealed_bundle,
            Path(temp) / "verified",
            EXPECTED_PLATFORM,
            EXPECTED_ARCHITECTURE,
            RC1_SECURITY_SEQUENCE,
            current_release_id=RC1_RELEASE_ID,
        )

    if bootstrap_result.get("security_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise BuildError("bootstrap did not verify RC.2 sequence 22")
    if bootstrap_result.get("release_id") != release_id:
        raise BuildError("bootstrap release id differs from signed candidate")
    if bootstrap_result.get("commit") != candidate.get("source_revision"):
        raise BuildError("bootstrap verified a different source revision")

    signed_copy = output_dir / f"{release_id}.metadata.signed.json"
    shutil.copyfile(signed_metadata_path, signed_copy)
    manifest_copy = output_dir / f"{release_id}.manifest.json"
    shutil.copyfile(candidate_dir / manifest_name, manifest_copy)
    bootstrap_copy = output_dir / "hive-bootstrap.pyz"
    shutil.copyfile(candidate_dir / "hive-bootstrap.pyz", bootstrap_copy)

    publishable_hashes = {
        sealed_bundle.name: _sha256(sealed_bundle),
        signed_copy.name: _sha256(signed_copy),
        manifest_copy.name: _sha256(manifest_copy),
        bootstrap_copy.name: _sha256(bootstrap_copy),
    }
    sums = "".join(f"{digest}  {name}\n" for name, digest in sorted(publishable_hashes.items()))
    (output_dir / "SHA256SUMS").write_text(sums, encoding="utf-8")

    receipt = {
        "status": "publishable_after_external_review",
        "version": EXPECTED_VERSION,
        "release_id": release_id,
        "security_sequence": EXPECTED_SECURITY_SEQUENCE,
        "previous_release_id": RC1_RELEASE_ID,
        "previous_security_sequence": RC1_SECURITY_SEQUENCE,
        "source_revision": candidate.get("source_revision"),
        "production_key_id": candidate.get("expected_production_key_id"),
        "sealed_bundle": sealed_bundle.name,
        "sealed_bundle_sha256": publishable_hashes[sealed_bundle.name],
        "manifest_digest": bootstrap_result.get("manifest_digest"),
        "bootstrap_root_fingerprint": bootstrap_result.get("root_fingerprint"),
        "bootstrap_verified": True,
        "seal_result": {key: str(value) if isinstance(value, Path) else value for key, value in seal_result.items()},
    }
    (output_dir / "PUBLISHABLE.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m release_engine.candidate_gate")
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--signed-metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = gate_candidate(args.candidate_dir, args.signed_metadata, args.output)
    except Exception as exc:
        print(f"[candidate-gate] {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
