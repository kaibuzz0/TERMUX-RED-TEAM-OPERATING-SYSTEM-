"""Non-mutating update planner."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from updates.errors import BundleError
from updates.manifest import load_manifest


def plan_update(bundle_root: Path, active_root: Path | None) -> dict[str, Any]:
    """Compare a staged bundle against the active runtime and produce a non-mutating plan."""
    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.exists():
        raise BundleError("Bundle missing manifest.json")
    manifest = load_manifest(manifest_path)

    current_files: dict[str, dict[str, Any]] = {}
    if active_root and active_root.exists():
        for entry in load_active_manifest(active_root):
            current_files[entry["path"]] = entry

    added = []
    changed = []
    removed = []
    unchanged = []

    for entry in manifest:
        rel = entry["path"]
        if rel not in current_files:
            added.append(rel)
        elif current_files[rel]["sha256"] != entry["sha256"]:
            changed.append(rel)
        else:
            unchanged.append(rel)

    for rel in current_files:
        if rel not in {e["path"] for e in manifest}:
            removed.append(rel)

    total_size = sum(e["size"] for e in manifest)

    return {
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged": unchanged,
        "artifact_count": len(manifest),
        "total_size": total_size,
        "rollback_point": str(active_root) if active_root and active_root.exists() else None,
        "configuration_migration": None,
        "vault_compatibility": "preserved",
        "warnings": [],
    }


def load_active_manifest(active_root: Path) -> list[dict[str, Any]]:
    path = active_root / "manifest.json"
    if not path.exists():
        return []
    return load_manifest(path)
