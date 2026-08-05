"""Release manifest generation and validation."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from updates.errors import BundleError


EXCLUDED_PREFIXES = (
    ".git",
    "blueprints",
    "tests",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "logs",
    ".hermes",
    ".hive",
    ".hive_auth",
    "vault.json",
)

EXCLUDED_FILES = {
    ".env",
    ".envrc",
    "secrets.yaml",
    "config.yaml",
    "session.db",
    "agent.log",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_executable(path: Path) -> bool:
    try:
        return bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except Exception:
        return False


def build_manifest(source_dir: Path, base_dir: Path | None = None) -> list[dict[str, Any]]:
    """Build a deterministic manifest of runtime artifacts under source_dir."""
    source_dir = source_dir.resolve()
    base_dir = (base_dir or source_dir).resolve()
    entries: list[dict[str, Any]] = []
    for root, dirs, files in os.walk(source_dir):
        # Filter excluded directories in-place to avoid descending
        dirs[:] = [d for d in dirs if not d.startswith(EXCLUDED_PREFIXES)]
        for f in files:
            if f.startswith(".") and f != ".termux":
                continue
            if f in EXCLUDED_FILES:
                continue
            full = Path(root) / f
            rel = full.relative_to(base_dir).as_posix()
            if any(rel.startswith(p) or rel.startswith(p + "/") for p in EXCLUDED_PREFIXES):
                continue
            entries.append({
                "path": rel,
                "size": full.stat().st_size,
                "sha256": _sha256(full),
                "executable": _is_executable(full),
                "type": "required",
            })
    entries.sort(key=lambda e: e["path"])
    return entries


def write_manifest(manifest: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")


def load_manifest(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise BundleError("Manifest must be a JSON list")
    return data


def verify_manifest(manifest: list[dict[str, Any]], bundle_root: Path) -> None:
    """Verify every manifest entry exists in bundle_root with matching digest."""
    seen: set[str] = set()
    for entry in manifest:
        rel = entry.get("path")
        if not rel:
            raise BundleError("Manifest entry missing path")
        if rel in seen:
            raise BundleError(f"Duplicate manifest path: {rel}")
        seen.add(rel)
        full = bundle_root / rel
        if not full.exists():
            raise BundleError(f"Missing artifact: {rel}")
        if full.stat().st_size != entry.get("size", -1):
            raise BundleError(f"Size mismatch: {rel}")
        digest = _sha256(full)
        if digest != entry.get("sha256"):
            raise BundleError(f"Digest mismatch: {rel}")
