"""Deterministic release builder."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from release_engine.errors import BuildError
from release_engine.manifest import build_release_manifest, manifest_digest
from release_engine.reproducibility import (
    ReproducibilityClass,
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

    Returns a dict describing the release artifact and manifest.
    """
    try:
        parse_release_version(version)
    except Exception as exc:
        raise BuildError(f"invalid version: {exc}") from exc

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
            "channel": channel,
            "build_id": build_id,
            "source_revision": source_revision,
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

    # Write manifest and metadata alongside the bundle for inspection.
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
