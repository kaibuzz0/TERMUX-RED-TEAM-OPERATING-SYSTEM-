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
