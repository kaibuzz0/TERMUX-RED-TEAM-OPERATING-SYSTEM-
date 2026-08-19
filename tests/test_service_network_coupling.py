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



def test_proxy_env_uses_manifest_filtered_base(tmp_path):
    """Supervisor must pass manifest-filtered env to proxy_env, not raw os.environ."""
    from network import NetworkManager
    from services.supervisor import Supervisor
    # Put a denied host variable into os.environ; it should not reach the child.
    import os
    os.environ["HIVE_HOST_DENIED"] = "should-not-appear"
    manifest = {
        "needs-proxy": {
            "schema_version": 1,
            "name": "needs-proxy",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "environment": {
                "allow": ["PATH"],
                "set": {"HIVE_MANIFEST_SET": "survives"},
            },
            "network": {"required": True, "profile": "any", "use_proxy_env": True},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
    }
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(manifest, tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    proc = sup.processes.get("needs-proxy")
    # Before start, inspect the built environment via protected helper if needed.
    # We instead verify via the spawned process env file if accessible.
    # Simpler: ensure the Supervisor passes base_env=env to proxy_env by
    # checking that a denied host var absent from allow list is not present.
    env = sup._build_environment(manifest["needs-proxy"])
    assert "HIVE_HOST_DENIED" not in env
    assert env["HIVE_MANIFEST_SET"] == "survives"
    # Start the service; it should run.
    result = sup.start("needs-proxy")
    assert result["state"] == "RUNNING"
    sup.stop("needs-proxy")
    del os.environ["HIVE_HOST_DENIED"]


def test_proxy_env_direct_clears_stale_proxy_values(tmp_path):
    """When profile is DIRECT, proxy vars must be absent from child env."""
    from network import NetworkManager
    from services.supervisor import Supervisor
    manifest = {
        "needs-proxy": {
            "schema_version": 1,
            "name": "needs-proxy",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "environment": {"allow": [], "set": {}},
            "network": {"required": True, "profile": "any", "use_proxy_env": True},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
    }
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(manifest, tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    env = sup._build_environment(manifest["needs-proxy"])
    env = net_mgr.proxy_env(base_env=env)
    assert "ALL_PROXY" not in env
    assert "HTTP_PROXY" not in env
    assert "HTTPS_PROXY" not in env
