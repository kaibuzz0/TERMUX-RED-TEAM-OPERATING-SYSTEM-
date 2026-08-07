"""Regression tests proving plugin validation/install planning do not execute code."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from plugin_sdk.cli import main


def _manifest_with_evil_entrypoint() -> dict:
    return {
        "schema_version": 1,
        "plugin": {
            "id": "evil.noexec-test",
            "name": "Noexec Test Plugin",
            "version": "1.0.0",
            "sdk_version": "1.0",
            "entrypoint": "evil_module.raise_on_import",
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


def _evil_plugin_code() -> str:
    return """raise RuntimeError('PLUGIN CODE EXECUTED')
"""


class TestValidationDoesNotExecuteCode:
    def test_validate_directory_no_import(self, tmp_path):
        d = tmp_path / "plugin"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(_manifest_with_evil_entrypoint()), encoding="utf-8")
        (d / "evil_module.py").write_text(_evil_plugin_code(), encoding="utf-8")
        rc = main(["validate", str(d)])
        assert rc == 0

    def test_validate_bundle_no_import(self, tmp_path):
        bundle = tmp_path / "evil.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_manifest_with_evil_entrypoint()))
            zf.writestr("evil_module.py", _evil_plugin_code())
        rc = main(["validate", str(bundle)])
        assert rc == 0

    def test_install_plan_no_import(self, tmp_path):
        bundle = tmp_path / "evil.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_manifest_with_evil_entrypoint()))
            zf.writestr("evil_module.py", _evil_plugin_code())
        rc = main(["install", str(bundle), "--plan"])
        assert rc == 0

    def test_inspect_no_import(self, tmp_path):
        d = tmp_path / "plugin"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(_manifest_with_evil_entrypoint()), encoding="utf-8")
        (d / "evil_module.py").write_text(_evil_plugin_code(), encoding="utf-8")
        rc = main(["inspect", "--path", str(d)])
        assert rc == 0


class TestNoAutoEnable:
    def test_install_plan_auto_enable_false(self, tmp_path):
        bundle = tmp_path / "plugin.zip"
        manifest = _manifest_with_evil_entrypoint()
        manifest["plugin"]["id"] = "auto.enable-test"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("evil_module.py", _evil_plugin_code())
        rc = main(["install", str(bundle), "--plan"])
        assert rc == 0
