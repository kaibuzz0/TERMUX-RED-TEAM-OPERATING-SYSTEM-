"""Tests for service supervisor basics."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from services.supervisor import Supervisor


def _simple_manifest(name: str = "test-svc"):
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


def test_supervisor_starts_and_stops_service(tmp_path):
    sup = Supervisor(_simple_manifest(), tmp_path, tmp_path / "logs", {})
    result = sup.start("test-svc")
    assert result["state"] == "RUNNING"
    assert result["pid"] is not None
    assert sup.status("test-svc")["state"] == "RUNNING"
    sup.stop("test-svc")
    assert sup.status("test-svc")["state"] == "STOPPED"


def test_supervisor_global_status(tmp_path):
    sup = Supervisor(_simple_manifest(), tmp_path, tmp_path / "logs", {})
    sup.start("test-svc")
    global_status = sup.status()
    assert global_status["services_running"] == 1
    assert "services" in global_status
    sup.stop("test-svc")


def test_supervisor_ps(tmp_path):
    sup = Supervisor(_simple_manifest(), tmp_path, tmp_path / "logs", {})
    sup.start("test-svc")
    rows = sup.ps()
    assert len(rows) == 1
    assert rows[0]["service"] == "test-svc"
    sup.stop("test-svc")
