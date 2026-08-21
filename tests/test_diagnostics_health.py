"""Tests for `hive health`."""

from __future__ import annotations

from pathlib import Path

from diagnostics import evaluate_health
from network import NetworkManager
from services.supervisor import Supervisor


def _manifest(name: str = "test"):
    return {
        name: {
            "schema_version": 1,
            "name": name,
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        }
    }


def test_health_healthy_when_service_running(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifest(), tmp_path / "svc", tmp_path / "logs", {})
    sup.start("test")
    report = evaluate_health(net_mgr, sup)
    assert report.overall == "healthy"
    sup.stop("test")


def test_health_default_hold_profile_is_degraded_not_failed(tmp_path):
    """A fresh uninstalled source checkout has no selected network profile.

    This is intentional defensive state, not a failure.  Health must report
    DEGRADED with a clear H-NET-001 finding, never FAILED.
    """
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    assert net_mgr.current_profile.name.lower() == "hold"
    sup = Supervisor(_manifest(), tmp_path / "svc", tmp_path / "logs", {})
    report = evaluate_health(net_mgr, sup)
    assert report.overall == "degraded"
    assert report.components["network"] == "degraded"
    hnet001 = [f for f in report.findings if f.code == "H-NET-001"]
    assert hnet001, "expected H-NET-001 finding for unconfigured network profile"
    assert hnet001[0].severity.name == "WARNING"
    assert "not configured" in hnet001[0].message.lower()


def test_health_degraded_with_blocked_service(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    manifests = {
        "needs-tor": {
            "schema_version": 1,
            "name": "needs-tor",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "network": {"required": True, "profile": "tor"},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        }
    }
    sup = Supervisor(manifests, tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    sup.start("needs-tor")
    report = evaluate_health(net_mgr, sup)
    assert report.overall == "degraded"
