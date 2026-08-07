"""Hive Status example plugin.

Read-only, no network, no secrets, no filesystem mutation.
Disabled by default; requires explicit enable after review.
"""

from __future__ import annotations

from plugin_sdk.broker_client import create_plugin_client
from plugin_sdk.identity import PluginIdentity


def main(identity: PluginIdentity, granted_capabilities: list[str]) -> dict:
    """Return plugin status without executing mutations."""
    client = create_plugin_client(identity, granted_capabilities)
    status = client.status()
    return {
        "plugin_id": status["plugin_id"],
        "granted_capabilities": status["granted_capabilities"],
        "read_only": True,
        "network": "deny",
        "secrets": [],
    }
