"""Post-installation verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class VerificationError(Exception):
    """Verification failure."""



def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_staged_manifest(staging_root: Path, manifest_path: Path | None = None, runtime_subdir: str = "data/runtime") -> dict[str, Any]:
    """Verify staged files match the recorded manifest."""
    if manifest_path is None:
        manifest_path = staging_root / "state" / "manifest.json"
    if not manifest_path.exists():
        raise VerificationError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    manifest = data.get("manifest", [])
    errors = []
    verified = 0

    for entry in manifest:
        rel = entry["path"]
        expected = entry.get("sha256")
        base = staging_root / runtime_subdir
        file_path = base / rel
        if entry["type"] == "directory":
            if not file_path.is_dir():
                errors.append(f"Missing directory: {rel}")
            continue
        if not file_path.is_file():
            errors.append(f"Missing file: {rel}")
            continue
        if expected and _hash_file(file_path) != expected:
            errors.append(f"Hash mismatch: {rel}")
        verified += 1

    return {
        "verified_files": verified,
        "errors": errors,
        "valid": not errors,
    }
