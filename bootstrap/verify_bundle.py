#!/usr/bin/env python3
"""Standalone Hive bootstrap verifier for clean Termux installs.

This module intentionally has no imports from the Hive source tree. A clean
Termux install can install Python + python-cryptography, download a release
bundle, and verify it before any code from that bundle is executed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

ROOT_KEY_ID = "hive-release-prod-2026-03"
ROOT_KEY_FINGERPRINT = "1c55f45db250153c7045ff85526c56355adedbf0673ddb52e73ccbca9905835f"
ROOT_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA5bI3SLvvOBOM2rbrjK1f+dlTLczf/0a9looWt8RmbO4=
-----END PUBLIC KEY-----
"""
MAX_SECURITY_SEQUENCE = 2_147_483_647
MAX_ARCHIVE_MEMBERS = 100_000
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
CONTROL_FILES = frozenset({"metadata.json", "manifest.json"})


class BootstrapVerificationError(RuntimeError):
    """A release failed a clean-install bootstrap verification gate."""


def _canonical_json(data: dict[str, Any]) -> bytes:
    def reject_float(value: Any) -> None:
        if isinstance(value, float):
            raise BootstrapVerificationError("floats are not permitted in signed metadata")
        if isinstance(value, dict):
            for item in value.values():
                reject_float(item)
        elif isinstance(value, list):
            for item in value:
                reject_float(item)

    reject_float(data)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_root_key() -> Ed25519PublicKey:
    key = load_pem_public_key(ROOT_KEY_PEM)
    if not isinstance(key, Ed25519PublicKey):
        raise BootstrapVerificationError("embedded Hive root key is not Ed25519")
    raw = key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = hashlib.sha256(raw).hexdigest()
    if fingerprint != ROOT_KEY_FINGERPRINT:
        raise BootstrapVerificationError("embedded Hive root key fingerprint mismatch")
    return key


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise BootstrapVerificationError(f"unsafe archive/manifest path: {value!r}")
    if "\\" in value or "\x00" in value:
        raise BootstrapVerificationError(f"unsafe archive/manifest path: {value!r}")
    return path


def _prepare_extract_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise BootstrapVerificationError("bootstrap extraction destination must not be a symlink")
    if destination.exists():
        if not destination.is_dir():
            raise BootstrapVerificationError("bootstrap extraction destination must be a directory")
        try:
            if next(destination.iterdir(), None) is not None:
                raise BootstrapVerificationError("bootstrap extraction destination must be empty")
        except OSError as exc:
            raise BootstrapVerificationError(f"cannot inspect bootstrap extraction destination: {exc}") from exc
    else:
        destination.mkdir(parents=True)
    destination.chmod(0o700)


def safe_extract(bundle: Path, destination: Path) -> None:
    """Extract an archive without delegating filesystem writes to ``tarfile``.

    Only regular files and directories are accepted. The destination must be an
    empty, non-symlink directory; archive path-prefix conflicts are rejected;
    member count and total uncompressed bytes are bounded before any payload is
    written. Tar header permission bits are ignored.
    """
    _prepare_extract_destination(destination)
    try:
        archive = tarfile.open(bundle, "r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise BootstrapVerificationError(f"invalid release archive: {exc}") from exc

    with archive:
        members = archive.getmembers()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise BootstrapVerificationError("release archive contains too many members")

        seen_members: set[str] = set()
        regular_files: set[str] = set()
        normalized_members: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
        extracted_bytes = 0

        for member in members:
            rel_path = _safe_relative_path(member.name)
            normalized = rel_path.as_posix()
            if normalized in seen_members:
                raise BootstrapVerificationError(f"duplicate archive member: {member.name}")
            seen_members.add(normalized)
            if not (member.isfile() or member.isdir()):
                raise BootstrapVerificationError(f"unsafe archive member type: {member.name}")
            if member.isfile():
                if member.size < 0:
                    raise BootstrapVerificationError(f"invalid archive member size: {member.name}")
                extracted_bytes += member.size
                if extracted_bytes > MAX_EXTRACTED_BYTES:
                    raise BootstrapVerificationError("release archive exceeds bootstrap extraction limit")
                regular_files.add(normalized)
            normalized_members.append((member, rel_path))

        # A regular file may never be an ancestor of another archive path. This
        # catches ambiguous archives such as a file named ``a`` plus ``a/b``.
        for _member, rel_path in normalized_members:
            for depth in range(1, len(rel_path.parts)):
                ancestor = PurePosixPath(*rel_path.parts[:depth]).as_posix()
                if ancestor in regular_files:
                    raise BootstrapVerificationError(f"archive path conflicts with regular file: {ancestor}")

        for member, rel_path in normalized_members:
            target = destination.joinpath(*rel_path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                if target.is_symlink() or not target.is_dir():
                    raise BootstrapVerificationError(f"unsafe extracted directory: {member.name}")
                target.chmod(0o700)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            parent = destination
            for part in rel_path.parts[:-1]:
                parent = parent / part
                if parent.is_symlink() or not parent.is_dir():
                    raise BootstrapVerificationError(f"unsafe extraction parent: {member.name}")
                parent.chmod(0o700)
            if target.exists() or target.is_symlink():
                raise BootstrapVerificationError(f"archive target already exists: {member.name}")

            source = archive.extractfile(member)
            if source is None:
                raise BootstrapVerificationError(f"archive member is unreadable: {member.name}")
            remaining = member.size
            try:
                with target.open("xb") as handle:
                    while remaining:
                        chunk = source.read(min(65536, remaining))
                        if not chunk:
                            raise BootstrapVerificationError(f"truncated archive member: {member.name}")
                        handle.write(chunk)
                        remaining -= len(chunk)
                target.chmod(0o600)
            except Exception:
                target.unlink(missing_ok=True)
                raise


def verify_metadata(metadata: dict[str, Any]) -> None:
    if metadata.get("schema_version") != 1:
        raise BootstrapVerificationError("unsupported metadata schema")
    release = metadata.get("release")
    if not isinstance(release, dict):
        raise BootstrapVerificationError("release metadata missing")
    sequence = release.get("security_sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 0 <= sequence <= MAX_SECURITY_SEQUENCE:
        raise BootstrapVerificationError("invalid security sequence")
    signing = metadata.get("signing")
    if not isinstance(signing, dict):
        raise BootstrapVerificationError("signing block missing")
    if signing.get("algorithm") != "Ed25519":
        raise BootstrapVerificationError("unsupported signing algorithm")
    if signing.get("key_id") != ROOT_KEY_ID:
        raise BootstrapVerificationError(
            f"bootstrap release must be signed by {ROOT_KEY_ID}; got {signing.get('key_id')!r}"
        )
    encoded = signing.get("signature")
    if not isinstance(encoded, str) or not encoded:
        raise BootstrapVerificationError("metadata signature missing")
    unsigned = dict(metadata)
    unsigned["signing"] = {"algorithm": "Ed25519", "key_id": ROOT_KEY_ID, "signature": ""}
    try:
        signature = base64.urlsafe_b64decode(encoded.encode("ascii"))
        _load_root_key().verify(signature, _canonical_json(unsigned))
    except Exception as exc:
        if isinstance(exc, BootstrapVerificationError):
            raise
        raise BootstrapVerificationError("metadata signature verification failed") from exc


def _verify_manifest_closure(destination: Path, manifest_paths: set[str]) -> None:
    """Require the extracted file set to be exactly the signed manifest plus controls."""
    expected = set(manifest_paths) | set(CONTROL_FILES)
    actual: set[str] = set()
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise BootstrapVerificationError(f"unsafe extracted symlink: {path.relative_to(destination).as_posix()}")
        if path.is_file():
            actual.add(path.relative_to(destination).as_posix())
    extras = sorted(actual - expected)
    if extras:
        raise BootstrapVerificationError(f"unmanifested bundle file: {extras[0]}")
    missing = sorted(expected - actual)
    if missing:
        raise BootstrapVerificationError(f"missing bundle file: {missing[0]}")


def verify_bundle(
    bundle: Path,
    destination: Path,
    platform: str,
    architecture: str,
    current_sequence: int,
    current_release_id: str | None = None,
) -> dict[str, Any]:
    if current_sequence < 0:
        raise BootstrapVerificationError("current security sequence cannot be negative")
    if current_release_id is not None and (not isinstance(current_release_id, str) or not current_release_id):
        raise BootstrapVerificationError("current release id must be a non-empty string when supplied")

    safe_extract(bundle, destination)
    metadata_path = destination / "metadata.json"
    manifest_path = destination / "manifest.json"
    if not metadata_path.is_file() or not manifest_path.is_file():
        raise BootstrapVerificationError("bundle missing metadata.json or manifest.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise BootstrapVerificationError("metadata must be an object")
    verify_metadata(metadata)
    release = metadata["release"]
    if platform not in release.get("platforms", []):
        raise BootstrapVerificationError(f"release does not support platform {platform}")
    if architecture not in release.get("architectures", []):
        raise BootstrapVerificationError(f"release does not support architecture {architecture}")

    sequence = release["security_sequence"]
    release_id = release.get("release_id")
    if sequence < current_sequence:
        raise BootstrapVerificationError(
            f"release sequence {sequence} is older than current sequence {current_sequence}"
        )
    if sequence == current_sequence and current_release_id is not None and release_id != current_release_id:
        raise BootstrapVerificationError(
            f"security sequence {sequence} already belongs to release {current_release_id}"
        )

    expected_manifest = metadata.get("manifest_digest")
    actual_manifest = _sha256_file(manifest_path)
    if not isinstance(expected_manifest, str) or expected_manifest != actual_manifest:
        raise BootstrapVerificationError("manifest digest mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise BootstrapVerificationError("manifest must be a list")
    seen: set[str] = set()
    for entry in manifest:
        if not isinstance(entry, dict):
            raise BootstrapVerificationError("invalid manifest entry")
        rel = entry.get("path")
        if not isinstance(rel, str):
            raise BootstrapVerificationError("manifest entry missing path")
        _safe_relative_path(rel)
        if rel in CONTROL_FILES:
            raise BootstrapVerificationError(f"manifest must not redefine bootstrap control file: {rel}")
        if rel in seen:
            raise BootstrapVerificationError(f"duplicate manifest path: {rel}")
        seen.add(rel)
        full = destination / rel
        if not full.is_file() or full.is_symlink():
            raise BootstrapVerificationError(f"missing or unsafe artifact: {rel}")
        if full.stat().st_size != entry.get("size"):
            raise BootstrapVerificationError(f"size mismatch: {rel}")
        if _sha256_file(full) != entry.get("sha256"):
            raise BootstrapVerificationError(f"sha256 mismatch: {rel}")
    _verify_manifest_closure(destination, seen)
    return {
        "verified": True,
        "version": release.get("version"),
        "release_id": release_id,
        "commit": release.get("commit"),
        "security_sequence": sequence,
        "key_id": ROOT_KEY_ID,
        "root_fingerprint": ROOT_KEY_FINGERPRINT,
        "manifest_digest": actual_manifest,
        "bundle_root": str(destination),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive-bootstrap-verify")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--platform", default="termux")
    parser.add_argument("--architecture", default=os.uname().machine if hasattr(os, "uname") else "aarch64")
    parser.add_argument("--current-sequence", type=int, default=0)
    parser.add_argument("--current-release-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    destination = args.destination
    temporary = None
    if destination is None:
        temporary = tempfile.TemporaryDirectory(prefix="hive-bootstrap-")
        destination = Path(temporary.name)
    try:
        result = verify_bundle(
            args.bundle.resolve(),
            destination.resolve(),
            args.platform,
            args.architecture,
            args.current_sequence,
            current_release_id=args.current_release_id,
        )
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Hive release verified: {result['release_id']} ({result['version']})")
            print(f"Signer: {result['key_id']}")
            print(f"Manifest: {result['manifest_digest']}")
        return 0
    except (BootstrapVerificationError, json.JSONDecodeError, OSError) as exc:
        print(f"Hive bootstrap verification failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
