"""Persistent plugin registry.

Resolves Milestone 16 in-memory limitation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from release_engine.errors import RegistryError


@dataclass
class PluginRegistryRecord:
    plugin_id: str
    version: str
    installation_id: str
    manifest_digest: str
    bundle_digest: str
    signature_trust: str
    requested_capabilities: List[str]
    granted_capabilities: List[str]
    configuration_digest: str
    state: str
    install_timestamp: str
    publisher: str | None
    sdk_compatibility: str
    quarantine_state: str | None


class PersistentPluginRegistry:
    """Atomic JSON-backed plugin registry under the state root."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "plugins": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.parent / f".{self.path.name}.tmp"
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def list_plugins(self) -> List[PluginRegistryRecord]:
        return [self._record(v) for v in self._data.get("plugins", {}).values()]

    def _record(self, raw: Dict[str, Any]) -> PluginRegistryRecord:
        return PluginRegistryRecord(**raw)

    def get(self, plugin_id: str) -> PluginRegistryRecord | None:
        raw = self._data.get("plugins", {}).get(plugin_id)
        return self._record(raw) if raw else None

    def register(self, record: PluginRegistryRecord) -> None:
        plugins = self._data.setdefault("plugins", {})
        if record.plugin_id in plugins:
            raise RegistryError(f"plugin already registered: {record.plugin_id}")
        plugins[record.plugin_id] = record.__dict__
        self._save()

    def set_state(self, plugin_id: str, state: str) -> None:
        plugins = self._data.get("plugins", {})
        if plugin_id not in plugins:
            raise RegistryError(f"plugin not registered: {plugin_id}")
        plugins[plugin_id]["state"] = state
        self._save()
