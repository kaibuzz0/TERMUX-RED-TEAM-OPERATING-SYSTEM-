"""Plugin SDK CLI tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from plugin_sdk.cli import main
from plugin_sdk.errors import PluginManifestError


def _valid_manifest(plugin_id: str = "hive.status-example") -> dict:
    return {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": "Hive Status Example Plugin",
            "version": "1.0.0",
            "sdk_version": "1.0",
            "entrypoint": "hive_status_example.main",
            "type": "client",
        },
        "compatibility": {
            "minimum_hive_version": "1.0.0-dev",
            "required_broker_version": "1.0",
            "required_capabilities": ["service.status", "broker.status"],
        },
        "permissions": {
            "requested_capabilities": ["service.status"],
            "filesystem": [],
            "network": "deny",
            "secrets": [],
        },
        "lifecycle": {"auto_start": False},
    }


class TestCliValidate:
    def test_cli_validate_directory(self, tmp_path, capsys):
        d = tmp_path / "plugin"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(_valid_manifest()), encoding="utf-8")
        rc = main(["validate", str(d)])
        captured = capsys.readouterr()
        assert rc == 0
        assert json.loads(captured.out)["valid"] is True

    def test_cli_validate_bundle(self, tmp_path, capsys):
        bundle = tmp_path / "plugin.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_valid_manifest()))
            zf.writestr("plugin.py", "# ok")
        rc = main(["validate", str(bundle)])
        captured = capsys.readouterr()
        assert rc == 0
        assert json.loads(captured.out)["valid"] is True

    def test_cli_validate_rejects_shell(self, tmp_path, capsys):
        d = tmp_path / "bad"
        d.mkdir()
        m = _valid_manifest()
        m["permissions"]["requested_capabilities"] = ["shell"]
        (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        rc = main(["validate", str(d)])
        assert rc == 1

    def test_cli_validate_rejects_wildcard(self, tmp_path, capsys):
        d = tmp_path / "bad"
        d.mkdir()
        m = _valid_manifest()
        m["permissions"]["requested_capabilities"] = ["service.*"]
        (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        rc = main(["validate", str(d)])
        assert rc == 1


class TestCliInstallPlan:
    def test_install_plan(self, tmp_path, capsys):
        bundle = tmp_path / "plugin.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(_valid_manifest()))
            zf.writestr("plugin.py", "# ok")
        rc = main(["install", str(bundle), "--plan"])
        captured = capsys.readouterr()
        assert rc == 0
        plan = json.loads(captured.out)
        assert plan["action"] == "plan"
        assert plan["auto_enable"] is False


class TestCliNoExecShellInstallUrl:
    def test_no_exec_command(self, tmp_path, capsys):
        # exec command is not implemented; parser should reject.
        with pytest.raises(SystemExit):
            main(["exec", "foo"])

    def test_no_shell_command(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            main(["shell", "foo"])

    def test_no_install_url(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            main(["install-url", "http://example.com/x.zip"])
