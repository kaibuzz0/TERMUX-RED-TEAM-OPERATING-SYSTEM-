"""Read-only Operations Center plugin view."""

from __future__ import annotations

from typing import Any, Dict

from plugin_sdk.registry import PluginRegistry


def plugin_list_view(registry: PluginRegistry | None = None) -> Dict[str, Any]:
    """Return read-only plugin list for Operations Center."""
    reg = registry or PluginRegistry()
    return {
        "view": "plugins",
        "count": len(reg.list_plugins()),
        "plugins": [
            {
                "id": entry.identity.plugin_id,
                "version": entry.identity.plugin_version,
                "state": entry.lifecycle.state,
                "manifest_digest": entry.identity.manifest_digest,
            }
            for entry in reg.list_plugins()
        ],
    }
