"""Tests for `hive selftest`."""

from __future__ import annotations

from pathlib import Path

from diagnostics import run_selftest
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


def test_selftest_restores_profile(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifest(), tmp_path / "svc", tmp_path / "logs", {})
    result = run_selftest(net_mgr, sup, tmp_path, steps=[])
    assert result["overall"] == "PASS"
    assert net_mgr.current_profile.name == "DIRECT"


def test_selftest_reports_failing_step(tmp_path):
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifest(), tmp_path / "svc", tmp_path / "logs", {})

    def fail_step(_, __):
        raise RuntimeError("intentional failure")

    result = run_selftest(net_mgr, sup, tmp_path, steps=[fail_step])
    assert result["overall"] == "FAIL"
    assert any(s["name"] == "fail_step" and s["result"] == "FAIL" for s in result["steps"])
    assert net_mgr.current_profile.name == "DIRECT"


def test_selftest_no_leaked_processes(tmp_path):
    """Verify selftest does not leave services running unintentionally."""
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    sup = Supervisor(_manifest(), tmp_path / "svc", tmp_path / "logs", {})
    result = run_selftest(net_mgr, sup, tmp_path, steps=[])
    assert sup.status("test")["state"] == "STOPPED"
    assert result["overall"] == "PASS"
    assert not result["restore_errors"]
    assert net_mgr.current_profile.name == "DIRECT"
    # Ensure no pid remains recorded in state
    assert sup.status("test")["pid"] is None

