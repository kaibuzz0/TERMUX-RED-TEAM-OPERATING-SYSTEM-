"""Plugin bundle loading and staging.

Installation is staged; no code executes during validation, inspection, or planning.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from plugin_sdk.errors import PluginBundleError, PluginManifestError
from plugin_sdk.manifest import load_manifest, manifest_digest
from plugin_sdk.schema import MAX_BUNDLE_FILES, MAX_BUNDLE_PATH_LENGTH, MAX_BUNDLE_SIZE


def stage_bundle(
    bundle_path: Path,
    stage_root: Path,
    expected_plugin_id: str | None = None,
) -> Path:
    """Extract a plugin bundle into a staging directory with safety checks.

    Does not execute any plugin code.
    """
    if not bundle_path.exists():
        raise PluginBundleError(f"bundle not found: {bundle_path}")

    size = bundle_path.stat().st_size
    if size > MAX_BUNDLE_SIZE:
        raise PluginBundleError(f"bundle size {size} exceeds {MAX_BUNDLE_SIZE}")

    stage_dir = stage_root / f"{bundle_path.stem}_{hashlib.sha256(bundle_path.name.encode()).hexdigest()[:16]}"
    stage_dir.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(bundle_path):
        with zipfile.ZipFile(bundle_path, "r") as zf:
            if len(zf.namelist()) > MAX_BUNDLE_FILES:
                raise PluginBundleError(f"bundle file count exceeds {MAX_BUNDLE_FILES}")
            seen = set()
            for info in zf.infolist():
                name = info.filename
                if len(name) > MAX_BUNDLE_PATH_LENGTH:
                    raise PluginBundleError(f"bundle path too long: {name}")
                if name.startswith("/") or ".." in name.split("/") or ".." in name.split(chr(92)):
                    raise PluginBundleError(f"path traversal rejected: {name}")
                # Reject symlinks and hardlinks via mode bits in external_attr.
                high = info.external_attr >> 16
                if high:
                    # Unix file type bits occupy top 4 bits of mode.
                    file_type = (high & 0o170000)
                    if file_type == 0o120000:
                        raise PluginBundleError(f"symlink rejected: {name}")
                    if file_type == 0o100000:
                        pass  # regular file
                    elif file_type:
                        raise PluginBundleError(f"special file rejected: {name}")
                if name.endswith("/"):
                    continue
                lower = name.lower()
                if ".tar" in lower or ".gz" in lower:
                    # Nested archives rejected by default in Milestone 16.
                    raise PluginBundleError(f"nested archive rejected: {name}")
                if name in seen:
                    raise PluginBundleError(f"duplicate entry: {name}")
                seen.add(name)
            zf.extractall(stage_dir)
    else:
        raise PluginBundleError("only ZIP bundles supported in Milestone 16")

    manifest_path = stage_dir / "manifest.json"
    if not manifest_path.exists():
        raise PluginBundleError("bundle missing manifest.json")

    manifest = load_manifest(manifest_path)
    if expected_plugin_id is not None and manifest["plugin"]["id"] != expected_plugin_id:
        raise PluginBundleError(f"plugin ID mismatch: expected {expected_plugin_id}")

    return stage_dir


def inspect_bundle(bundle_path: Path) -> Dict[str, Any]:
    """Inspect a bundle without staging or executing code."""
    if not bundle_path.exists():
        raise PluginBundleError(f"bundle not found: {bundle_path}")

    size = bundle_path.stat().st_size
    if size > MAX_BUNDLE_SIZE:
        raise PluginBundleError(f"bundle size {size} exceeds {MAX_BUNDLE_SIZE}")

    if not zipfile.is_zipfile(bundle_path):
        raise PluginBundleError("only ZIP bundles supported in Milestone 16")

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        if len(names) > MAX_BUNDLE_FILES:
            raise PluginBundleError(f"bundle file count exceeds {MAX_BUNDLE_FILES}")
        has_manifest = any(name == "manifest.json" for name in names)
        return {
            "size": size,
            "files": names,
            "manifest_present": has_manifest,
            "digest": manifest_digest(zf.read("manifest.json")) if has_manifest else None,
        }
