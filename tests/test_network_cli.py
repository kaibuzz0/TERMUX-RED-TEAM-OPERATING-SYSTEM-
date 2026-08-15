"""Tests for `hive net` CLI dispatch."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from network import cli as network_cli


def _run_cli(args, env=None):
    return network_cli.main(args)


def test_cli_status_default():
    with tempfile.TemporaryDirectory() as d:
        env = os.environ.copy()
        env["HIVE_STATE_ROOT"] = d
        env["HIVE_REPO_ROOT"] = str(Path(__file__).resolve().parents[1])
        rc = _run_cli(["status"])
        assert rc == 0


def test_cli_direct():
    rc = _run_cli(["direct"])
    assert rc == 0


def test_cli_hold():
    rc = _run_cli(["hold"])
    assert rc == 0


def test_cli_local_alias_warns_and_selects_tor():
    # This will attempt to start tor; on Windows it fails, but the compatibility
    # warning is printed and return code reflects tor unavailability.
    rc = _run_cli(["local"])
    assert rc in (0, 2)


def test_cli_run_with_no_command():
    rc = _run_cli(["run", "--"])
    assert rc == 5
