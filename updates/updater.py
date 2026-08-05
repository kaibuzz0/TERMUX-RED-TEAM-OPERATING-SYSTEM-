"""Update application using the installer activation engine."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from updates.errors import BundleError, UpdateError
from updates.planner import plan_update


class Updater:
    """Apply a verified bundle to the active runtime through staging and activation."""

    def __init__(self, release_root: Path):
        self.release_root = release_root
        self.journal_path = release_root / "update-history.json"

    def plan(self, bundle_root: Path) -> dict[str, Any]:
        active = self._active_release_root()
        return plan_update(bundle_root, active)

    def _active_release_root(self) -> Path | None:
        pointer = self.release_root / "active"
        if not pointer.exists():
            return None
        rel = pointer.read_text(encoding="utf-8").strip()
        return (self.release_root / rel) if rel else None

    def stage(self, bundle_root: Path) -> Path:
        """Stage the bundle into a new release directory under the release root."""
        from updates.metadata import parse_metadata
        metadata = parse_metadata((bundle_root / "metadata.json").read_text(encoding="utf-8"))
        release_id = metadata["release"]["release_id"]
        target = self.release_root / release_id
        if target.exists():
            raise BundleError(f"Release {release_id} already staged")
        _copy_tree(bundle_root, target)
        return target

    def record_history(self, metadata: dict[str, Any], prior_release: str | None, rollback: bool = False) -> None:
        entries = []
        if self.journal_path.exists():
            entries = json.loads(self.journal_path.read_text(encoding="utf-8"))
        entries.append({
            "release_id": metadata["release"]["release_id"],
            "version": metadata["release"]["version"],
            "commit": metadata["release"]["commit"],
            "security_sequence": metadata["release"]["security_sequence"],
            "prior_release": prior_release,
            "rollback": rollback,
            "timestamp": _now(),
        })
        self.journal_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _copy_tree(src: Path, dst: Path) -> None:
    import shutil
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
