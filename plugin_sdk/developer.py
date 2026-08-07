"""Developer utilities for Plugin SDK.

Helpers for scaffolding safe, read-only example plugins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from plugin_sdk import SCHEMA_VERSION, SDK_VERSION
from plugin_sdk.manifest import manifest_to_json


def scaffold_manifest(
    plugin_id: str,
    name: str,
    plugin_type: str = "client",
    requested_capabilities: list[str] | None = None,
) -> Dict[str, Any]:
    if requested_capabilities is None:
        requested_capabilities = ["service.status"]
    return {
        "schema_version": SCHEMA_VERSION,
        "plugin": {
            "id": plugin_id,
            "name": name,
            "version": "1.0.0",
            "sdk_version": SDK_VERSION,
            "entrypoint": f"{plugin_id.replace('-', '_').replace('.', '_')}.main",
            "type": plugin_type,
        },
        "compatibility": {
            "minimum_hive_version": "1.0.0-dev",
            "required_broker_version": "1.0",
            "required_capabilities": requested_capabilities,
        },
        "permissions": {
            "requested_capabilities": requested_capabilities,
            "filesystem": [],
            "network": "deny",
            "secrets": [],
        },
        "lifecycle": {
            "auto_start": False,
        },
    }


def write_example_plugin(directory: Path, plugin_id: str, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    manifest = scaffold_manifest(plugin_id, name)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    module_name = plugin_id.replace("-", "_").replace(".", "_")
    (directory / f"{module_name}.py").write_text(
        f'"""{name} example plugin."""\n\n'
        f"from plugin_sdk.broker_client import create_plugin_client\n"
        f"from plugin_sdk.identity import PluginIdentity\n\n"
        f"def main(identity: PluginIdentity, granted: list[str]) -> dict:\n"
        f'    client = create_plugin_client(identity, granted)\n'
        f'    return client.status()\n',
        encoding="utf-8",
    )
