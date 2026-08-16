"""Deterministic release builder."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from release_engine.errors import BuildError
from release_engine.manifest import build_release_manifest, manifest_digest
from release_engine.reproducibility import (
    ReproducibilityClass,
    _add_json,
    compute_bundle_digest,
    create_reproducible_tar,
)
from release_engine.schema import ReleaseMetadata
from release_engine.version import parse_release_version


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_release(
    source_dir: Path,
    output_dir: Path,
    version: str,
    release_sequence: int,
    build_id: str,
    source_revision: str,
    platforms: List[str],
    architectures: List[str],
    channel: str = "stable",
    minimum_supported_version: str = "0.0.0",
) -> Dict[str, Any]:
    """Build a deterministic release package.

    ``release_sequence`` remains the release-engine/registry ordering field.
    ``security_sequence`` is emitted as an equal-value compatibility field for
    the clean-install bootstrap's anti-rollback gate.  Keeping both prevents
    either side of the release pipeline from silently interpreting a different
    monotonic sequence.

    Returns a dict describing the release artifact and manifest.
    """
    try:
        parse_release_version(version)
    except Exception as exc:
        raise BuildError(f"invalid version: {exc}") from exc

    if not isinstance(release_sequence, int) or isinstance(release_sequence, bool) or release_sequence < 0:
        raise BuildError("release sequence must be a non-negative integer")

    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_release_manifest(source_dir)
    digest = manifest_digest(manifest)

    release_id = f"hive-os-{version}-{build_id}"
    bundle_name = f"{release_id}.tar.gz"
    bundle_path = output_dir / bundle_name

    metadata: Dict[str, Any] = {
        "schema_version": 1,
        "release": {
            "release_id": release_id,
            "version": version,
            "release_sequence": release_sequence,
            "security_sequence": release_sequence,
            "channel": channel,
            "build_id": build_id,
            "source_revision": source_revision,
            "commit": source_revision,
            "created_at": _now(),
            "minimum_supported_version": minimum_supported_version,
            "platforms": platforms,
            "architectures": architectures,
        },
        "manifest_digest": digest,
        "signing": {"algorithm": "Ed25519", "key_id": "", "signature": ""},
        "revocation": {"sequence": 0},
    }

    classification = create_reproducible_tar(source_dir, bundle_path, manifest, metadata)
    artifact_digests = {bundle_name: compute_bundle_digest(bundle_path)}

    # Write manifest and metadata alongside the bundle for inspection/offline
    # signing.  The signed sidecar must later be sealed back into the bundle;
    # the clean-install bootstrap verifies metadata from inside the archive.
    (output_dir / f"{release_id}.manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    unsigned_metadata = dict(metadata)
    (output_dir / f"{release_id}.metadata.json").write_text(
        json.dumps(unsigned_metadata, indent=2, sort_keys=True), encoding="utf-8"
    )

    return {
        "release_id": release_id,
        "version": version,
        "bundle_path": bundle_path,
        "bundle_digest": artifact_digests[bundle_name],
        "manifest_digest": digest,
        "metadata": metadata,
        "classification": classification.value,
        "artifact_digests": artifact_digests,
    }


def _json_member(archive: tarfile.TarFile, name: str) -> tuple[dict[str, Any], bytes]:
    members = [member for member in archive.getmembers() if member.name == name]
    if len(members) != 1 or not members[0].isfile():
        raise BuildError(f"release bundle must contain exactly one regular {name}")
    handle = archive.extractfile(members[0])
    if handle is None:
        raise BuildError(f"release bundle {name} is unreadable")
    raw = handle.read()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"release bundle {name} is invalid JSON") from exc
    if not isinstance(value, dict) and name == "metadata.json":
        raise BuildError("release bundle metadata.json must be an object")
    return value, raw


def seal_release_bundle(
    bundle_path: Path,
    signed_metadata: Dict[str, Any],
    output_path: Path,
) -> Dict[str, Any]:
    """Seal signed metadata back into a built release bundle.

    ``release sign`` operates on the inspectable metadata sidecar so private-key
    use can remain offline.  A publishable release, however, must carry that
    exact signed metadata *inside* the archive because the clean bootstrap does
    not trust unsigned sidecars.  This function refuses to alter any unsigned
    metadata field or to seal metadata for a different manifest.
    """
    bundle_path = bundle_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not bundle_path.is_file():
        raise BuildError(f"release bundle not found: {bundle_path}")
    if not isinstance(signed_metadata, dict):
        raise BuildError("signed metadata must be an object")

    signing = signed_metadata.get("signing")
    if not isinstance(signing, dict):
        raise BuildError("signed metadata is missing signing block")
    if signing.get("algorithm") != "Ed25519" or not signing.get("key_id") or not signing.get("signature"):
        raise BuildError("signed metadata must contain an Ed25519 key id and signature")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tarfile.open(bundle_path, "r:gz") as source:
            names = [member.name for member in source.getmembers()]
            if len(names) != len(set(names)):
                raise BuildError("release bundle contains duplicate members")

            original_metadata, _ = _json_member(source, "metadata.json")
            manifest_member = [member for member in source.getmembers() if member.name == "manifest.json"]
            if len(manifest_member) != 1 or not manifest_member[0].isfile():
                raise BuildError("release bundle must contain exactly one regular manifest.json")
            manifest_handle = source.extractfile(manifest_member[0])
            if manifest_handle is None:
                raise BuildError("release bundle manifest.json is unreadable")
            manifest_raw = manifest_handle.read()
            actual_manifest_digest = hashlib.sha256(manifest_raw).hexdigest()
            if signed_metadata.get("manifest_digest") != actual_manifest_digest:
                raise BuildError("signed metadata manifest digest does not match bundle manifest")

            original_unsigned = dict(original_metadata)
            original_unsigned["signing"] = {"algorithm": "Ed25519", "key_id": "", "signature": ""}
            candidate_unsigned = dict(signed_metadata)
            candidate_unsigned["signing"] = {"algorithm": "Ed25519", "key_id": "", "signature": ""}
            if candidate_unsigned != original_unsigned:
                raise BuildError("signed metadata changes unsigned bundle metadata")

            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=output_path.parent,
                prefix=".hive-seal-",
                suffix=".tar.gz",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)

            with tarfile.open(temp_path, "w:gz") as target:
                for member in source.getmembers():
                    if member.name == "metadata.json":
                        continue
                    if not member.isfile():
                        raise BuildError(f"release bundle contains unsupported member type: {member.name}")
                    payload = source.extractfile(member)
                    if payload is None:
                        raise BuildError(f"release bundle member is unreadable: {member.name}")
                    target.addfile(copy.copy(member), payload)
                _add_json(target, "metadata.json", signed_metadata)

        os.replace(temp_path, output_path)
        temp_path = None
    except (tarfile.TarError, OSError) as exc:
        raise BuildError(f"failed to seal release bundle: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return {
        "bundle_path": output_path,
        "bundle_digest": compute_bundle_digest(output_path),
        "manifest_digest": signed_metadata["manifest_digest"],
        "release_id": signed_metadata.get("release", {}).get("release_id"),
        "key_id": signing.get("key_id"),
        "sealed": True,
    }
