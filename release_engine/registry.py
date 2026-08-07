"""Persistent local release registry."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from release_engine.errors import RegistryError


REGISTRY_SCHEMA_VERSION = 1


@dataclass
class ReleaseRecord:
    release_id: str
    version: str
    release_sequence: int
    channel: str
    manifest_digest: str
    bundle_digest: str
    signing_key_id: str
    active: bool = False
    previous: bool = False
    activation_timestamp: str | None = None
    verified: bool = True


class ReleaseRegistry:
    """Atomic JSON-backed release registry."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": REGISTRY_SCHEMA_VERSION, "releases": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RegistryError(f"failed to load release registry: {exc}") from exc

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.parent / f".{self.path.name}.tmp"
        tmp.write_text(
            json.dumps(self._data, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def list_releases(self) -> List[ReleaseRecord]:
        return [self._record(r) for r in self._data.get("releases", [])]

    def _record(self, raw: Dict[str, Any]) -> ReleaseRecord:
        return ReleaseRecord(**raw)

    def get_active(self) -> ReleaseRecord | None:
        for r in self._data.get("releases", []):
            if r.get("active"):
                return self._record(r)
        return None

    def register(self, record: ReleaseRecord) -> None:
        releases = self._data.get("releases", [])
        for r in releases:
            if r["release_id"] == record.release_id:
                raise RegistryError(f"release already registered: {record.release_id}")
        releases.append(record.__dict__)
        self._save()

    def activate(self, release_id: str, timestamp: str | None = None) -> None:
        releases = self._data.get("releases", [])
        for r in releases:
            if r.get("active"):
                r["active"] = False
                r["previous"] = True
            if r["release_id"] == release_id:
                r["active"] = True
                r["previous"] = False
                r["activation_timestamp"] = timestamp
        self._save()

    def rollback_eligible(self) -> List[ReleaseRecord]:
        return [self._record(r) for r in self._data.get("releases", []) if r.get("previous")]
