"""Tests for layered network health model."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from network.health import HealthCheck, HealthLevel, HealthReport
from network.manager import NetworkManager
from network.errors import ProfileTransitionError, TorNotAvailableError
from network.profiles import NetworkProfile


def test_health_direct():
    with tempfile.TemporaryDirectory() as d:
        mgr = NetworkManager(state_root=Path(d))
        mgr.select_direct()
        report = mgr.health()
        assert report.level == HealthLevel.HEALTHY
        assert report.overall == "healthy"


def test_health_hold():
    with tempfile.TemporaryDirectory() as d:
        mgr = NetworkManager(state_root=Path(d))
        report = mgr.health()
        assert report.level == HealthLevel.UNAVAILABLE
        assert report.overall == "unavailable"


def test_health_orbot_without_orbot_is_unavailable():
    with tempfile.TemporaryDirectory() as d:
        mgr = NetworkManager(state_root=Path(d))
        mgr.select_orbot()
        report = mgr.health()
        assert report.level == HealthLevel.UNAVAILABLE
        assert not report.checks["socks_listener"]["ok"]


def test_health_tor_without_binary_is_unavailable():
    with tempfile.TemporaryDirectory() as d:
        mgr = NetworkManager(state_root=Path(d))
        with pytest.raises((TorNotAvailableError, ProfileTransitionError)):
            mgr.select_tor()
        report = mgr.health()
        assert report.level == HealthLevel.UNAVAILABLE


def test_port_open_does_not_mean_tor_healthy():
    # A hypothetical service listening on a port is not Tor.  The health model
    # requires bootstrap/process evidence, not just listener.
    report = HealthReport.from_results(
        "tor",
        {
            HealthCheck.SOCKS_LISTENER: (True, "port open"),
            HealthCheck.TOR_PROCESS: (False, "no tor process"),
            HealthCheck.CONTROL_PORT: (False, "no control port"),
            HealthCheck.BOOTSTRAP: (False, "bootstrap unknown"),
        },
    )
    assert report.level != HealthLevel.HEALTHY


def test_health_report_serialization():
    report = HealthReport.from_results(
        "direct",
        {HealthCheck.SOCKS_LISTENER: (True, "ok")},
    )
    data = report.to_dict()
    assert data["level"] == "HEALTHY"
    assert "socks_listener" in data["checks"]
