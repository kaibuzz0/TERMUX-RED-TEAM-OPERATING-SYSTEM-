from __future__ import annotations

import shutil
import subprocess
import sys
import zipapp
from pathlib import Path


def _build_zipapp(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    source = tmp_path / "bootstrap-src"
    shutil.copytree(repo_root / "bootstrap", source)
    archive = tmp_path / "hive-bootstrap.pyz"
    zipapp.create_archive(source, target=archive, interpreter="/usr/bin/env python3")
    return archive


def test_bootstrap_zipapp_legacy_install_help_runs_without_package_parent(tmp_path: Path) -> None:
    archive = _build_zipapp(tmp_path)
    result = subprocess.run(
        [sys.executable, str(archive), "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "hive-bootstrap-install" in result.stdout
    assert "--bundle-url" in result.stdout


def test_bootstrap_zipapp_explicit_install_help(tmp_path: Path) -> None:
    archive = _build_zipapp(tmp_path)
    result = subprocess.run(
        [sys.executable, str(archive), "install", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "hive-bootstrap-install" in result.stdout
    assert "--current-release-id" in result.stdout


def test_bootstrap_zipapp_verify_help(tmp_path: Path) -> None:
    archive = _build_zipapp(tmp_path)
    result = subprocess.run(
        [sys.executable, str(archive), "verify", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "hive-bootstrap-verify" in result.stdout
    assert "--current-release-id" in result.stdout
    assert "bundle" in result.stdout
