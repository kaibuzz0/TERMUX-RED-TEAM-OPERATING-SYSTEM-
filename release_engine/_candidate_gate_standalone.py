"""Self-contained post-sign gate used by the offline RC.2 zipapp.

The module intentionally avoids imports from the rest of ``release_engine`` so
an offline signing kit needs only this module, the clean bootstrap package, the
Python standard library, and the bootstrap's crypto dependency.  No private-key
handling is implemented here.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import os
import shutil
import stat
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from bootstrap.verify_bundle import verify_bundle, verify_metadata

RC1_RELEASE_ID = "hive-os-1.1.0-rc.1-20260815-parity"
RC1_SECURITY_SEQUENCE = 21
EXPECTED_VERSION = "1.1.0-rc.2"
EXPECTED_SECURITY_SEQUENCE = 22
EXPECTED_PLATFORM = "termux"
EXPECTED_ARCHITECTURE = "aarch64"


class CandidateGateError(RuntimeError):
    """The candidate cannot cross the post-sign release boundary."""


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
        raise CandidateGateError(f"invalid JSON file {path}: {exc}") from exc


def _unsigned_view(metadata: dict[str, Any]) -> dict[str, Any]:
    value = dict(metadata)
    value["signing"] = {"algorithm": "Ed25519", "key_id": "", "signature": ""}
    return value


def verify_candidate_hashes(candidate_dir: Path) -> dict[str, str]:
    sums_path = candidate_dir / "SHA256SUMS"
    if not sums_path.is_file():
        raise CandidateGateError("candidate kit is missing SHA256SUMS")

    verified: dict[str, str] = {}
    for line_number, raw in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise CandidateGateError(f"invalid SHA256SUMS line {line_number}")
        expected, name = parts[0], parts[1].strip()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise CandidateGateError(f"invalid SHA-256 digest on line {line_number}")
        path = Path(name)
        if path.name != name or path.is_absolute() or name in {".", ".."}:
            raise CandidateGateError(f"SHA256SUMS must contain basename-only paths: {name!r}")
        artifact = candidate_dir / name
        if not artifact.is_file():
            raise CandidateGateError(f"candidate hash target is missing: {name}")
        actual = _sha256(artifact)
        if actual != expected:
            raise CandidateGateError(f"candidate hash mismatch: {name}")
        if name in verified:
            raise CandidateGateError(f"duplicate SHA256SUMS entry: {name}")
        verified[name] = actual

    if not verified:
        raise CandidateGateError("candidate SHA256SUMS is empty")
    return verified


def validate_signed_metadata(
    candidate: dict[str, Any], unsigned_metadata: dict[str, Any], signed_metadata: dict[str, Any]
) -> None:
    if _unsigned_view(signed_metadata) != _unsigned_view(unsigned_metadata):
        raise CandidateGateError("signed metadata does not belong to the exact unsigned candidate")

    signing = signed_metadata.get("signing")
    if not isinstance(signing, dict):
        raise CandidateGateError("signed metadata is missing signing block")
    expected_key_id = candidate.get("expected_production_key_id")
    if signing.get("algorithm") != "Ed25519":
        raise CandidateGateError("signed candidate must use Ed25519")
    if not isinstance(expected_key_id, str) or not expected_key_id:
        raise CandidateGateError("candidate does not declare expected production key id")
    if signing.get("key_id") != expected_key_id:
        raise CandidateGateError(
            f"signed candidate must use production key {expected_key_id}; got {signing.get('key_id')!r}"
        )
    if not isinstance(signing.get("signature"), str) or not signing["signature"]:
        raise CandidateGateError("signed candidate has no signature")

    release = signed_metadata.get("release")
    if not isinstance(release, dict):
        raise CandidateGateError("signed candidate is missing release metadata")
    if release.get("version") != EXPECTED_VERSION:
        raise CandidateGateError(f"unexpected candidate version: {release.get('version')!r}")
    if release.get("security_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise CandidateGateError("RC.2 security sequence must be exactly 22")
    if release.get("release_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise CandidateGateError("RC.2 release sequence must be exactly 22")
    if release.get("platforms") != [EXPECTED_PLATFORM]:
        raise CandidateGateError("RC.2 candidate platform contract mismatch")
    if release.get("architectures") != [EXPECTED_ARCHITECTURE]:
        raise CandidateGateError("RC.2 candidate architecture contract mismatch")
    if release.get("commit") != candidate.get("source_revision"):
        raise CandidateGateError("signed candidate commit does not match CANDIDATE.json")
    if release.get("source_revision") != candidate.get("source_revision"):
        raise CandidateGateError("signed candidate source revision does not match CANDIDATE.json")
    if candidate.get("security_sequence") != EXPECTED_SECURITY_SEQUENCE:
        raise CandidateGateError("CANDIDATE.json does not carry RC.2 sequence 22")
    if candidate.get("rc1_sequence") != RC1_SECURITY_SEQUENCE:
        raise CandidateGateError("CANDIDATE.json RC.1 baseline is not sequence 21")

    # Actual Ed25519 verification against the public production root embedded
    # in the clean-install bootstrap.  This does not possess signing ability.
    verify_metadata(signed_metadata)


def _json_member(archive: tarfile.TarFile, name: str) -> tuple[Any, bytes]:
    members = [member for member in archive.getmembers() if member.name == name]
    if len(members) != 1 or not members[0].isfile():
        raise CandidateGateError(f"release bundle must contain exactly one regular {name}")
    handle = archive.extractfile(members[0])
    if handle is None:
        raise CandidateGateError(f"release bundle {name} is unreadable")
    raw = handle.read()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateGateError(f"release bundle {name} is invalid JSON") from exc
    return value, raw


def _normalize_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = stat.S_IMODE(info.mode)
    return info


@contextmanager
def _open_reproducible_tar(output_path: Path) -> Iterator[tarfile.TarFile]:
    with output_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                yield archive


def _add_json(archive: tarfile.TarFile, name: str, data: Any) -> None:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    _normalize_tar_info(info)
    archive.addfile(info, io.BytesIO(raw))


def seal_release_bundle(
    bundle_path: Path, signed_metadata: dict[str, Any], output_path: Path
) -> dict[str, Any]:
    """Seal signed metadata into the exact unsigned candidate deterministically."""
    bundle_path = bundle_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not bundle_path.is_file():
        raise CandidateGateError(f"release bundle not found: {bundle_path}")

    signing = signed_metadata.get("signing")
    if not isinstance(signing, dict):
        raise CandidateGateError("signed metadata is missing signing block")
    if signing.get("algorithm") != "Ed25519" or not signing.get("key_id") or not signing.get("signature"):
        raise CandidateGateError("signed metadata must contain an Ed25519 key id and signature")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tarfile.open(bundle_path, "r:gz") as source:
            members = source.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)):
                raise CandidateGateError("release bundle contains duplicate members")

            original_metadata, _ = _json_member(source, "metadata.json")
            manifest_value, manifest_raw = _json_member(source, "manifest.json")
            if not isinstance(original_metadata, dict) or not isinstance(manifest_value, list):
                raise CandidateGateError("release bundle metadata/manifest shape is invalid")
            if signed_metadata.get("manifest_digest") != hashlib.sha256(manifest_raw).hexdigest():
                raise CandidateGateError("signed metadata manifest digest does not match bundle manifest")
            if _unsigned_view(signed_metadata) != _unsigned_view(original_metadata):
                raise CandidateGateError("signed metadata changes unsigned bundle metadata")

            with tempfile.NamedTemporaryFile(
                mode="wb", dir=output_path.parent, prefix=".hive-seal-", suffix=".tar.gz", delete=False
            ) as handle:
                temp_path = Path(handle.name)

            with _open_reproducible_tar(temp_path) as target:
                for member in members:
                    if member.name == "metadata.json":
                        continue
                    if not member.isfile():
                        raise CandidateGateError(
                            f"release bundle contains unsupported member type: {member.name}"
                        )
                    payload = source.extractfile(member)
                    if payload is None:
                        raise CandidateGateError(f"release bundle member is unreadable: {member.name}")
                    target.addfile(copy.copy(member), payload)
                _add_json(target, "metadata.json", signed_metadata)

        os.replace(temp_path, output_path)
        temp_path = None
    except (tarfile.TarError, OSError) as exc:
        raise CandidateGateError(f"failed to seal release bundle: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return {
        "bundle_path": output_path,
        "bundle_digest": _sha256(output_path),
        "manifest_digest": signed_metadata["manifest_digest"],
        "release_id": signed_metadata.get("release", {}).get("release_id"),
        "key_id": signing.get("key_id"),
        "sealed": True,
    }


def gate_candidate(candidate_dir: Path, signed_metadata_path: Path, output_dir: Path) -> dict[str, Any]:
    candidate_dir = candidate_dir.expanduser().resolve()
    signed_metadata_path = signed_metadata_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()

    if not candidate_dir.is_dir():
        raise CandidateGateError(f"candidate directory not found: {candidate_dir}")
    hashes = verify_candidate_hashes(candidate_dir)

    candidate = _read_json(candidate_dir / "CANDIDATE.json")
    if not isinstance(candidate, dict):
        raise CandidateGateError("CANDIDATE.json must be an object")
    if candidate.get("status") != "unsigned_candidate_only":
        raise CandidateGateError("candidate kit status is not unsigned_candidate_only")

    bundle_name = candidate.get("bundle")
    metadata_name = candidate.get("metadata")
    manifest_name = candidate.get("manifest")
    for label, name in (("bundle", bundle_name), ("metadata", metadata_name), ("manifest", manifest_name)):
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise CandidateGateError(f"candidate {label} name is unsafe")
        if name not in hashes:
            raise CandidateGateError(f"candidate {label} is not covered by SHA256SUMS: {name}")

    unsigned_metadata = _read_json(candidate_dir / metadata_name)
    signed_metadata = _read_json(signed_metadata_path)
    if not isinstance(unsigned_metadata, dict) or not isinstance(signed_metadata, dict):
        raise CandidateGateError("release metadata must be an object")
    validate_signed_metadata(candidate, unsigned_metadata, signed_metadata)

    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise CandidateGateError("publishable output directory must be empty")

    release_id = signed_metadata["release"].get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise CandidateGateError("signed candidate has no release id")
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
        raise CandidateGateError("bootstrap did not verify RC.2 sequence 22")
    if bootstrap_result.get("release_id") != release_id:
        raise CandidateGateError("bootstrap release id differs from signed candidate")
    if bootstrap_result.get("commit") != candidate.get("source_revision"):
        raise CandidateGateError("bootstrap verified a different source revision")

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
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(publishable_hashes.items())),
        encoding="utf-8",
    )

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
        "seal_result": {
            key: str(value) if isinstance(value, Path) else value for key, value in seal_result.items()
        },
    }
    (output_dir / "PUBLISHABLE.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="hive-release-gate.pyz")
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
