"""Tests for proxy environment and safe command runner."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from network.profiles import NetworkProfile
from network.proxy import build_proxy_env, is_proxy_execution_allowed, run_command
from network.state import NetworkState


def test_direct_clears_proxy_vars():
    base = {
        "ALL_PROXY": "socks5h://old:1",
        "HTTP_PROXY": "http://old:1",
        "HTTPS_PROXY": "http://old:1",
    }
    env = build_proxy_env(NetworkProfile.DIRECT, base_env=base)
    assert "ALL_PROXY" not in env
    assert "HTTP_PROXY" not in env
    assert env["NO_PROXY"] == "localhost,127.0.0.1,::1"


def test_tor_sets_socks5h_proxy():
    env = build_proxy_env(NetworkProfile.TOR)
    assert env["ALL_PROXY"] == "socks5h://127.0.0.1:9052"
    assert env["SOCKS5_SERVER"] == "127.0.0.1:9052"


def test_hold_disallows_proxy_run():
    state = NetworkState(profile="hold")
    allowed, reason = is_proxy_execution_allowed(state)
    assert not allowed
    assert "HOLD" in reason


def test_run_preserves_argument_vector():
    env = os.environ.copy()
    result = run_command(["python", "-c", "import sys; print('|'.join(sys.argv[1:]))"], env=env)
    assert result.returncode == 0


def test_run_child_exit_code_returned():
    env = os.environ.copy()
    result = run_command(["python", "-c", "import sys; sys.exit(42)"], env=env)
    assert result.returncode == 42
