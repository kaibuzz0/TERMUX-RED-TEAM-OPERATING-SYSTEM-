"""Tests for exact process ownership and clean shutdown."""

from __future__ import annotations

import tempfile
import sys
import time

import pytest
from pathlib import Path

from services.process import TrackedProcess


def test_tracked_process_identity(tmp_path):
    manifest = {"name": "test"}
    command = ["python", "-c", "import time; time.sleep(3600)"]
    proc = TrackedProcess(manifest, command, "session-1")
    proc.start(tmp_path, env={})
    assert proc.pid is not None
    assert proc.is_running()
    assert proc.validate_identity()
    result = proc.terminate("TERM", timeout=1.0, kill_after_timeout=True)
    assert result["signaled"]


def test_terminate_aborts_if_identity_invalid(tmp_path):
    manifest = {"name": "test"}
    command = ["python", "-c", "import time; time.sleep(3600)"]
    proc = TrackedProcess(manifest, command, "session-1")
    # Fake start_time mismatch will invalidate identity
    proc.start_time = 0
    result = proc.terminate("TERM", timeout=1.0, kill_after_timeout=True)
    assert not result["signaled"]
    assert result["reason"] == "no process"



def test_tracked_process_start_time_is_os_derived(tmp_path):
    """Ensure start_time is captured from OS identity, not wall-clock."""
    if sys.platform == "win32":
        pytest.importorskip("psutil", reason="Windows identity domain requires psutil; Linux/Termux uses /proc directly")
    manifest = {"name": "test"}
    command = ["python", "-c", "import time; time.sleep(3600)"]
    proc = TrackedProcess(manifest, command, "session-1")
    before_wall = time.time()
    proc.start(tmp_path, env={})
    after_wall = time.time()
    assert proc.pid is not None
    assert proc.start_time is not None
    # On Windows psutil.create_time() is wall-clock; on Linux /proc starttime is
    # boot-relative.  Either way it must not be a freshly minted time.time()
    # value from inside start() with no OS backing.
    assert proc.start_time < before_wall or proc.start_time <= after_wall
    # Most importantly: the value must round-trip through _process_start_time.
    from services.process import _process_start_time
    assert _process_start_time(proc.pid) is not None
    assert abs(_process_start_time(proc.pid) - proc.start_time) < 1
    proc.terminate("TERM", timeout=1.0, kill_after_timeout=True)


def test_supervisor_start_uses_tracked_process_identity(tmp_path):
    """Supervisor must spawn via TrackedProcess.start and capture OS identity."""
    from services.supervisor import Supervisor
    manifests = {
        "identity-test": {
            "schema_version": 1,
            "name": "identity-test",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
    }
    sup = Supervisor(manifests, tmp_path / "svc", tmp_path / "logs", {})
    result = sup.start("identity-test")
    assert result["state"] == "RUNNING"
    proc = sup.processes["identity-test"]
    assert proc.start_time is not None
    assert proc.validate_identity()
    stop_result = sup.stop("identity-test")
    assert stop_result["state"] == "STOPPED"


def test_supervisor_restart_preserves_identity(tmp_path):
    """Restart must stop and start with a fresh OS-derived identity."""
    from services.supervisor import Supervisor
    manifests = {
        "identity-test": {
            "schema_version": 1,
            "name": "identity-test",
            "enabled": True,
            "command": {"interpreter": "python", "args": ["-c", "import time; time.sleep(3600)"]},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
        },
    }
    sup = Supervisor(manifests, tmp_path / "svc", tmp_path / "logs", {})
    start1 = sup.start("identity-test")
    assert start1["state"] == "RUNNING"
    pid1 = sup.processes["identity-test"].pid
    restart = sup.restart("identity-test")
    assert restart["state"] == "RUNNING"
    pid2 = sup.processes["identity-test"].pid
    assert pid1 != pid2
    assert sup.processes["identity-test"].validate_identity()
    sup.stop("identity-test")
