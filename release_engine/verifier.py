"""Release verification adapter.

Wraps updates.verifier for release-specific verification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from updates.bundle import extract_bundle
from updates.errors import BundleError
from updates.manifest import load_manifest, verify_manifest
from updates.metadata import canonical_json
from updates.trust import TrustStore

from release_engine.errors import ReleaseFormatError
from release_engine.signing import verify_release_metadata


def inspect_release(bundle_path: Path, work_dir: Path) -> Dict[str, Any]:
    """Extract and inspect a release bundle without fully verifying trust."""
    work_dir.mkdir(parents=True, exist_ok=True)
    extract_bundle(bundle_path, work_dir)
    metadata_path = work_dir / "metadata.json"
    manifest_path = work_dir / "manifest.json"
    if not metadata_path.exists():
        raise ReleaseFormatError("release bundle missing metadata.json")
    if not manifest_path.exists():
        raise ReleaseFormatError("release bundle missing manifest.json")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    manifest = load_manifest(manifest_path)
    return {"metadata": metadata, "manifest": manifest}


def verify_release_bundle(
    bundle_path: Path,
    work_dir: Path,
    trust_store: TrustStore,
    current_sequence: int = 0,
    allow_emergency: bool = False,
) -> Dict[str, Any]:
    """Verify a release bundle: extract, verify manifest, trust, sequence."""
    work_dir.mkdir(parents=True, exist_ok=True)
    extract_bundle(bundle_path, work_dir)

    metadata_path = work_dir / "metadata.json"
    manifest_path = work_dir / "manifest.json"
    if not metadata_path.exists() or not manifest_path.exists():
        raise ReleaseFormatError("bundle missing metadata.json or manifest.json")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    manifest = load_manifest(manifest_path)

    # Trust verification
    verify_release_metadata(metadata, trust_store)

    # Manifest digest consistency
    expected_digest = metadata.get("manifest_digest", "")
    actual_digest = hashlib_digest(manifest)
    if expected_digest != actual_digest:
        raise ReleaseFormatError("manifest digest mismatch")

    # Verify manifest against payload files
    payload_root = work_dir
    verify_manifest(manifest, payload_root)

    # Anti-rollback
    seq = metadata.get("release", {}).get("release_sequence", 0)
    if seq <= current_sequence and not allow_emergency:
        raise ReleaseFormatError(f"release sequence {seq} not newer than {current_sequence}")

    return {"metadata": metadata, "manifest": manifest, "verified": True}


def hashlib_digest(manifest: Any) -> str:
    import hashlib
    import json

    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
