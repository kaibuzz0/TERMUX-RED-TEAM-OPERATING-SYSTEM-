"""Tiered recovery actions."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from updates.errors import UpdateError


class RecoveryLevel(Enum):
    DIAGNOSE = 0
    REPAIR_GENERATED_STATE = 1
    RESTORE_CURRENT_VERIFIED_RELEASE = 2
    ROLLBACK_PREVIOUS_RELEASE = 3
    RESTORE_OFFLINE_BUNDLE = 4
    DISASTER_RECOVERY = 5
    DESTRUCTIVE_RESET = 6


def diagnose(release_root: Path) -> dict[str, Any]:
    """Level 0: non-mutating diagnosis of release root."""
    active_pointer = release_root / "active"
    active = None
    if active_pointer.exists():
        active = active_pointer.read_text(encoding="utf-8").strip()
    result = {
        "release_root": str(release_root),
        "active_release": active,
        "pointer_exists": active_pointer.exists(),
        "releases": [p.name for p in release_root.iterdir() if p.is_dir()],
        "journal_exists": (release_root / "update-history.json").exists(),
        "locks": _scan_locks(release_root),
        "mutation": False,
    }
    return result


def repair_stale_locks(release_root: Path, max_age_seconds: int = 300) -> dict[str, Any]:
    """Level 1: remove stale lock files."""
    import time
    removed = []
    for lock in release_root.rglob("*.lock"):
        try:
            age = time.time() - lock.stat().st_mtime
            if age > max_age_seconds:
                lock.unlink()
                removed.append(str(lock))
        except Exception:
            pass
    return {"mutation": True, "removed_locks": removed}


def rollback_to_previous(release_root: Path, updater: Any) -> dict[str, Any]:
    """Level 3: rollback to previous release."""
    raise NotImplementedError("Rollback delegates to installer.rollback via the activation engine")


def restore_offline_bundle(release_root: Path, bundle_root: Path, updater: Any) -> dict[str, Any]:
    """Level 4: restore from a verified offline bundle while preserving state."""
    staged = updater.stage(bundle_root)
    return {"mutation": True, "staged_release": staged.name}


def _scan_locks(release_root: Path) -> list[str]:
    return [str(p.relative_to(release_root)) for p in release_root.rglob("*.lock")]
