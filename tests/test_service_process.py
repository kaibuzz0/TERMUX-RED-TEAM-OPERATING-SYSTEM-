"""Tests for exact process ownership and clean shutdown."""

from __future__ import annotations

import tempfile
import time
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
