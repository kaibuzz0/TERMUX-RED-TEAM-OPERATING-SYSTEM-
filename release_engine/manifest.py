"""Canonical deterministic release manifest.

Reuses updates.manifest for core manifest building.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from updates.errors import BundleError
from updates.manifest import build_manifest as _build_update_manifest

from release_engine.errors import ManifestError


def build_release_manifest(
    source_dir: Path,
    base_dir: Path | None = None,
    extra_excludes: set[str] | None = None,
) -> List[Dict[str, Any]]:
    """Build a deterministic, canonical manifest for a release.

    Excludes build/runtime/dev artifacts and secrets by default.
    """
    source_dir = source_dir.resolve()
    base_dir = (base_dir or source_dir).resolve()
    entries = _build_update_manifest(source_dir, base_dir)

    excludes = {
        ".git",
        ".github",
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
        ".env",
        ".envrc",
        "secrets.yaml",
        "config.yaml",
        "session.db",
        "agent.log",
        "gateway.log",
        "errors.log",
        "*.key",
        "*.pem",
        "*.p12",
    }
    if extra_excludes:
        excludes.update(extra_excludes)

    def _excluded(entry: Dict[str, Any]) -> bool:
        rel = entry["path"]
        if any(rel.startswith(e + "/") or rel == e for e in excludes):
            return True
        if any(rel.endswith(suffix) for suffix in (".key", ".pem", ".p12", ".env", ".db", ".log")):
            return True
        return False

    filtered = [e for e in entries if not _excluded(e)]
    # Enforce canonical deterministic ordering by relative path.
    return sorted(filtered, key=lambda e: e["path"])


def manifest_digest(entries: List[Dict[str, Any]]) -> str:
    """Deterministic digest of the canonical manifest."""
    canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
