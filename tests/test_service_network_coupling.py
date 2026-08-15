"""Tests for service supervisor network fail-closed coupling."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from network import NetworkManager
from services.supervisor import Supervisor


def _manifests():
    return {
        "needs-tor": {
            "schema_version": 1,
            "name": "needs-tor",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "network": {"required": True, "profile": "tor"},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
        "needs-orbot": {
            "schema_version": 1,
            "name": "needs-orbot",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "network": {"required": True, "profile": "orbot"},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
        "needs-proxied": {
            "schema_version": 1,
            "name": "needs-proxied",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "network": {"required": True, "profile": "proxied"},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
        "needs-any": {
            "schema_version": 1,
            "name": "needs-any",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "network": {"required": True, "profile": "any"},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
        "no-network": {
            "schema_version": 1,
            "name": "no-network",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
    }


def test_tor_service_blocked_in_direct(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("needs-tor")
    assert result["state"] == "BLOCKED_NETWORK"


def test_tor_service_blocked_in_hold(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_hold()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("needs-tor")
    assert result["state"] == "BLOCKED_NETWORK"


def test_orbot_service_blocked_in_tor(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    # On Windows tor binary is absent, so set TOR profile directly for the test.
    from network.state import update_profile
    from network.profiles import NetworkProfile
    update_profile(tmp_path / "net", NetworkProfile.TOR)
    net_mgr._load()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("needs-orbot")
    assert result["state"] == "BLOCKED_NETWORK"


def test_proxied_service_allows_tor(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    from network.state import update_profile
    from network.profiles import NetworkProfile
    update_profile(tmp_path / "net", NetworkProfile.TOR)
    net_mgr._load()
    # Bypass Tor binary availability for this coupling test.
    from network.health import HealthLevel
    class FakeHealth:
        overall = "healthy"
        level = HealthLevel.HEALTHY
        def to_dict(self):
            return {}
    net_mgr.health = lambda **kw: FakeHealth()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("needs-proxied")
    assert result["state"] != "BLOCKED_NETWORK"


def test_any_network_allows_direct(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("needs-any")
    assert result["state"] == "RUNNING"


def test_no_network_required_starts_in_hold(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_hold()
    sup = Supervisor(_manifests(), tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    result = sup.start("no-network")
    assert result["state"] == "RUNNING"
    sup.stop("no-network")
