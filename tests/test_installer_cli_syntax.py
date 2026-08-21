"""Regression tests for installer CLI documentation syntax.

Ensures the installer module docstring and README use the canonical subcommand
form (e.g. `installer.install check`) rather than the obsolete flag form
(`--check`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("bad", [
    "python3 -m installer.install --check",
    "python3 -m installer.install --plan",
    "python3 -m installer.install --dry-run",
    "python -m installer.install --check",
    "python -m installer.install --plan",
    "python -m installer.install --dry-run",
])
def test_installer_docs_do_not_use_obsolete_flag_syntax(bad: str) -> None:
    """Obsolete --check/--plan/--dry-run flags are not documented."""
    for path in ["installer/install.py", "installer/README.md", "README.md", "install.sh", "install-termux.sh"]:
        p = REPO_ROOT / path
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        assert bad not in text, f"obsolete installer syntax found in {path}: {bad}"


@pytest.mark.parametrize("good", [
    "python3 -m installer.install check",
    "python3 -m installer.install plan",
    "python3 -m installer.install dry-run",
    "python -m installer.install check",
    "python -m installer.install plan",
    "python -m installer.install dry-run",
])
def test_installer_docs_use_subcommand_syntax(good: str) -> None:
    """At least one documented file uses the canonical subcommand form."""
    found = False
    for path in ["installer/install.py", "installer/README.md", "README.md"]:
        p = REPO_ROOT / path
        if not p.exists():
            continue
        if good in p.read_text(encoding="utf-8"):
            found = True
            break
    assert found, f"canonical installer syntax not documented: {good}"
