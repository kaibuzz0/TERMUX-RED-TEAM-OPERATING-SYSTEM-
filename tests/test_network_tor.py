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
