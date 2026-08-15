"""Version and active release discovery for `hive version`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class VersionInfo:
    def __init__(self, data_root: Path | None = None, state_root: Path | None = None):
        self.data_root = data_root
        self.state_root = state_root
        self.active: dict[str, Any] | None = None
        self.release: dict[str, Any] | None = None
        self._load()

    def _load(self) -> None:
        if not self.data_root or not self.data_root.exists():
            return
        pointer = self.data_root / "active.json"
        if not pointer.exists():
            return
        try:
            self.active = json.loads(pointer.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        release_id = self.active.get("active_release_id")
        if not release_id:
            return
        release_json = self.data_root / "releases" / release_id / ".release.json"
        if release_json.exists():
            try:
                self.release = json.loads(release_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.release = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "version": None,
            "release_id": None,
            "channel": None,
            "commit": None,
            "active_runtime": None,
            "previous_release_id": None,
            "trust_level": None,
            "schema_version": 1,
        }
        if self.active:
            result["release_id"] = self.active.get("active_release_id")
            result["active_runtime"] = self.active.get("active_runtime")
            result["previous_release_id"] = self.active.get("previous_release_id")
        if self.release:
            meta = self.release.get("metadata", {})
            rel = meta.get("release", {})
            result["version"] = rel.get("version")
            result["channel"] = rel.get("channel")
            result["commit"] = rel.get("commit")
            result["trust_level"] = self.release.get("trust_level")
        return result


def get_active_version(data_root: Path | None = None, state_root: Path | None = None) -> VersionInfo:
    return VersionInfo(data_root, state_root)
