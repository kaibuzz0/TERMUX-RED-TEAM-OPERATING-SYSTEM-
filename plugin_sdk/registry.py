"""Plugin registry lifecycle.

Tracks DISCOVERED -> VALIDATED -> DISABLED state. Default state is DISABLED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from plugin_sdk.errors import PluginLifecycleError
from plugin_sdk.identity import PluginIdentity
from plugin_sdk.lifecycle import DEFAULT_STATE, PluginLifecycle
from plugin_sdk.manifest import load_manifest, manifest_digest


@dataclass
class PluginEntry:
    identity: PluginIdentity
    manifest: Dict[str, Any]
    lifecycle: PluginLifecycle
    stage_path: Path | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """In-memory plugin registry. Persistence is deferred to Config Engine."""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginEntry] = {}

    def discover(self, stage_path: Path) -> PluginEntry:
        manifest_path = stage_path / "manifest.json"
        manifest = load_manifest(manifest_path)
        digest = manifest_digest(manifest_path)
        identity = PluginIdentity.from_manifest(manifest, digest)

        entry = PluginEntry(
            identity=identity,
            manifest=manifest,
            lifecycle=PluginLifecycle(plugin_id=identity.plugin_id, state="DISCOVERED"),
            stage_path=stage_path,
        )
        self._plugins[identity.plugin_id] = entry
        return entry

    def validate(self, plugin_id: str) -> None:
        entry = self._get(plugin_id)
        entry.lifecycle.transition("VALIDATED")

    def set_state(self, plugin_id: str, state: str, reason: str = "") -> None:
        entry = self._get(plugin_id)
        entry.lifecycle.transition(state, reason)

    def get(self, plugin_id: str) -> PluginEntry:
        return self._get(plugin_id)

    def list_plugins(self) -> List[PluginEntry]:
        return list(self._plugins.values())

    def _get(self, plugin_id: str) -> PluginEntry:
        if plugin_id not in self._plugins:
            raise PluginLifecycleError(f"plugin not registered: {plugin_id}")
        return self._plugins[plugin_id]

    def remove(self, plugin_id: str) -> None:
        entry = self._get(plugin_id)
        entry.lifecycle.transition("REMOVED")
        del self._plugins[plugin_id]
