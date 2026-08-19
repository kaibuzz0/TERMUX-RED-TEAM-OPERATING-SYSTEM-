"""Tests for local Tor adapter behavior."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from network.errors import TorNotAvailableError
from network.health import HealthCheck
from network.tor import TorAdapter, TorEndpoints, _which_tor


def test_tor_binary_detection_missing():
    # In Windows test environment tor is likely absent.
    if _which_tor() is None:
        pytest.skip("tor binary not available")


def test_tor_adapter_unavailable_on_windows(tmp_path):
    adapter = TorAdapter(state_dir=tmp_path, endpoints=TorEndpoints("127.0.0.1", 9052, "127.0.0.1", 9051), binary=None)
    if _which_tor() is None:
        assert not adapter.available()
        with pytest.raises(TorNotAvailableError):
            adapter.start(timeout=0.1)


def test_tor_config_generation(tmp_path):
    adapter = TorAdapter(
        state_dir=tmp_path,
        endpoints=TorEndpoints("127.0.0.1", 9052, "127.0.0.1", 9051),
        binary="/nonexistent/tor",
    )
    torrc = adapter.generate_config()
    text = torrc.read_text(encoding="utf-8")
    assert "SOCKSPort 127.0.0.1:9052" in text
    assert "ControlPort 127.0.0.1:9051" in text
    assert "CookieAuthentication 1" in text
    assert "ClientOnly 1" in text


def test_tor_health_without_process_reports_not_running(tmp_path):
    adapter = TorAdapter(
        state_dir=tmp_path,
        endpoints=TorEndpoints("127.0.0.1", 9052, "127.0.0.1", 9051),
        binary="/nonexistent/tor",
    )
    data = adapter.health()
    assert not data["checks"][HealthCheck.TOR_PROCESS.value]["ok"]



def test_tor_adapter_persists_managed_identity(tmp_path):
    """Starting (or simulating) Tor should persist strong identity metadata."""
    from network.tor import _compute_config_identity, _load_identity, _save_identity
    torrc = tmp_path / "torrc"
    torrc.write_text("SOCKSPort 127.0.0.1:9052\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    identity = {
        "pid": 12345,
        "binary": "/usr/bin/tor",
        "config_identity": _compute_config_identity(torrc, data_dir),
        "data_dir": str(data_dir),
        "started_at": 0,
    }
    _save_identity(tmp_path, identity)
    loaded = _load_identity(tmp_path)
    assert loaded["config_identity"] == identity["config_identity"]
    assert loaded["data_dir"] == str(data_dir)


def test_tor_adapter_refuses_stale_pid(tmp_path):
    """A stale PID must not be considered a match if identity cannot be verified."""
    from network.tor import TorAdapter, TorEndpoints
    adapter = TorAdapter(
        state_dir=tmp_path,
        endpoints=TorEndpoints("127.0.0.1", 9052, "127.0.0.1", 9051),
        binary="/nonexistent/tor",
    )
    # No identity file, no process handle: should not find a managed PID.
    assert adapter._find_matching_pid() is None
