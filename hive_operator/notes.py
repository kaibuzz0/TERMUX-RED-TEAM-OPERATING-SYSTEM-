"""Operator notes management."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _notes_path(config_root: Path) -> Path:
    return config_root / "operator-notes.txt"


def _legacy_notes_path() -> Path:
    return Path.home() / ".hive_ops.txt"


def _migrate_legacy_notes(config_root: Path) -> bool:
    """Copy legacy notes to modern location if legacy exists and modern does not."""
    legacy = _legacy_notes_path()
    modern = _notes_path(config_root)
    if legacy.exists() and not modern.exists():
        modern.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(legacy), str(modern))
        return True
    return False


def read_notes(config_root: Path) -> tuple[str, bool]:
    migrated = _migrate_legacy_notes(config_root)
    path = _notes_path(config_root)
    if not path.exists():
        return "", migrated
    try:
        return path.read_text(encoding="utf-8"), migrated
    except OSError as exc:
        return f"[error reading notes: {exc}]", migrated


def save_notes(config_root: Path, content: str) -> Path:
    path = _notes_path(config_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if os.name == "posix":
        try:
            path.chmod(0o600)
        except (OSError, PermissionError):
            pass
    return path


def clear_notes(config_root: Path) -> bool:
    path = _notes_path(config_root)
    if path.exists():
        path.unlink()
        return True
    return False


def notes_info(config_root: Path) -> dict[str, Any]:
    migrated = _migrate_legacy_notes(config_root)
    path = _notes_path(config_root)
    info = {
        "modern_path": str(path),
        "legacy_path": str(_legacy_notes_path()),
        "migrated": migrated,
        "exists": path.exists(),
    }
    if path.exists():
        stat = path.stat()
        info["size_bytes"] = stat.st_size
        info["updated"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return info
