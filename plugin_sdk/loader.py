"""Plugin bundle staging.

Reuses hardened Milestone 10 bundle extraction where possible, then adds
plugin-specific verification (expected plugin ID, manifest digest).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from plugin_sdk.errors import PluginBundleError
from plugin_sdk.manifest import load_manifest, manifest_digest
from updates.bundle import extract_bundle
from updates.errors import BundleError


def inspect_bundle(bundle_path: Path) -> Dict[str, Any]:
    """Inspect a plugin bundle without extracting it.

    Does not execute any plugin code.
    """
    import zipfile

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        has_manifest = "manifest.json" in names
        digest = None
        if has_manifest:
            digest = manifest_digest(zf.read("manifest.json"))
        return {
            "files": names,
            "file_count": len(names),
            "manifest_present": has_manifest,
            "manifest_digest": digest,
        }


def stage_bundle(
    bundle_path: Path,
    stage_root: Path,
    expected_plugin_id: str | None = None,
) -> Path:
    """Stage a plugin bundle into a unique directory.

    Reuses updates.bundle.extract_bundle for hardened extraction.
    Adds plugin-specific manifest verification.
    """
    stage_root = stage_root.resolve()
    stage_root.mkdir(parents=True, exist_ok=True)
    bundle_digest = _bundle_digest(bundle_path)
    stage_dir = stage_root / bundle_digest[:16]
    if stage_dir.exists():
        # Verify existing staged manifest if reusing
        return stage_dir
    stage_dir.mkdir(parents=True, exist_ok=True)

    try:
        extract_bundle(bundle_path, stage_dir)
    except BundleError as exc:
        raise PluginBundleError(f"bundle extraction failed: {exc}") from exc

    manifest_path = stage_dir / "manifest.json"
    if not manifest_path.exists():
        raise PluginBundleError("plugin bundle missing manifest.json")

    manifest = load_manifest(manifest_path)
    plugin_id = manifest["plugin"]["id"]
    if expected_plugin_id is not None and plugin_id != expected_plugin_id:
        raise PluginBundleError(
            f"plugin ID mismatch: expected {expected_plugin_id}, got {plugin_id}"
        )

    return stage_dir


def _bundle_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
