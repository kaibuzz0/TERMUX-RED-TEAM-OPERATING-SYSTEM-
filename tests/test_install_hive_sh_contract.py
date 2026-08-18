from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "install-hive.sh"


import sys
import pytest

if sys.platform == "win32":
    pytest.skip(
        "bash-dependent contract test is POSIX-only",
        allow_module_level=True,
    )

def test_install_hive_shell_is_syntax_valid_and_documents_clean_bootstrap() -> None:
    syntax = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True, check=False)
    assert syntax.returncode == 0, syntax.stderr

    help_result = subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True, check=False)
    assert help_result.returncode == 0, help_result.stderr
    assert "clean-Termux bootstrap" in help_result.stdout
    assert "--bootstrap-sha256" in help_result.stdout
    assert "--bundle-url" in help_result.stdout


def test_install_hive_shell_rejects_insecure_urls_before_touching_termux() -> None:
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--bootstrap-url",
            "http://example.test/hive-bootstrap.pyz",
            "--bootstrap-sha256",
            "0" * 64,
            "--bundle-url",
            "https://example.test/hive.tar.gz",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "must use https://" in result.stderr


def test_install_hive_shell_preserves_operator_environment_contract() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "git clone" not in source
    assert "git reset" not in source
    assert "~/.hermes" in source
    assert "~/.ssh" in source
    assert ".bashrc" not in source
    assert ".zshrc" not in source
    assert "python-cryptography" in source
    assert "--approve" in source
    assert "--current-sequence" in source