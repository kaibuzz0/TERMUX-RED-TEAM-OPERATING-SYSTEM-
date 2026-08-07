"""Operations Center plugin view tests."""

from __future__ import annotations

import json

from operations_center.plugin_view import plugin_list_view
from plugin_sdk.registry import PluginRegistry


def test_plugin_list_empty():
    result = plugin_list_view()
    assert result["view"] == "plugins"
    assert result["count"] == 0


def test_plugin_list_with_registry(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    manifest = {
        "schema_version": 1,
        "plugin": {
            "id": "example.view",
            "name": "View Plugin",
            "version": "1.0.0",
            "sdk_version": "1.0",
            "entrypoint": "example.main",
            "type": "client",
        },
        "compatibility": {
            "minimum_hive_version": "1.0.0-dev",
            "required_broker_version": "1.0",
            "required_capabilities": ["service.status"],
        },
        "permissions": {
            "requested_capabilities": ["service.status"],
            "filesystem": [],
            "network": "deny",
            "secrets": [],
        },
        "lifecycle": {"auto_start": False},
    }
    (stage / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    reg = PluginRegistry()
    reg.discover(stage)
    result = plugin_list_view(reg)
    assert result["count"] == 1
    assert result["plugins"][0]["id"] == "example.view"
