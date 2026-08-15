"""Tests for `hive doctor`."""

from __future__ import annotations

from pathlib import Path

from diagnostics import diagnose
from network import NetworkManager
from services.supervisor import Supervisor


def test_doctor_finds_orbot_issue(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_orbot()
    sup = Supervisor({}, tmp_path / "svc", tmp_path / "logs", {}, network_manager=net_mgr)
    findings = diagnose(net_mgr, sup, tmp_path, tmp_path / "state", tmp_path / "logs")
    orbot_findings = [f for f in findings if f.code == "D-NET-002"]
    assert orbot_findings


def test_doctor_finds_blocked_service(tmp_path):
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
    findings = diagnose(net_mgr, sup, tmp_path, tmp_path / "state", tmp_path / "logs")
    blocked = [f for f in findings if f.code == "D-SVC-001"]
    assert blocked
