"""Tests for unified logging subsystem."""

from __future__ import annotations

from pathlib import Path

from runtime_logs.rotation import RotationPolicy, rotate, rotate_if_needed
from runtime_logs.service_logger import RuntimeLogger, ServiceLogger


def test_service_logger_creates_log(tmp_path):
    svc = tmp_path / "svc"
    log = ServiceLogger("mini-ai", tmp_path)
    handles = log.open_handles()
    handles["stdout"].write("hello stdout\n")
    handles["stderr"].write("hello stderr\n")
    log.close()
    assert (tmp_path / "services" / "mini-ai.log").exists()
    assert (tmp_path / "services" / "mini-ai.err.log").exists()


def test_rotate_creates_archive(tmp_path):
    base = tmp_path / "app.log"
    base.write_text("line\n" * 1000, encoding="utf-8")
    result = rotate(base, RotationPolicy(max_bytes=1, retention_count=3))
    assert result["rotated"]
    assert (tmp_path / "app.log.1.gz").exists()


def test_rotate_respects_retention(tmp_path):
    base = tmp_path / "app.log"
    for i in range(6):
        base.write_text(f"batch {i}\n", encoding="utf-8")
        rotate(base, RotationPolicy(retention_count=2))
    rotated = list(tmp_path.glob("app.log.*"))
    assert len(rotated) <= 2


def test_rotate_if_needed_threshold(tmp_path):
    base = tmp_path / "app.log"
    base.write_text("x", encoding="utf-8")
    result = rotate_if_needed(base, RotationPolicy(max_bytes=1024))
    assert not result["rotated"]


def test_runtime_logger_structured(tmp_path):
    logger = RuntimeLogger(tmp_path, "network")
    logger.write("PROFILE_CHANGE", "switched to TOR", {"old": "direct", "new": "tor"})
    entries = (tmp_path / "runtime" / "network.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(entries) == 1
    import json
    data = json.loads(entries[0])
    assert data["event"] == "PROFILE_CHANGE"
    assert data["metadata"]["new"] == "tor"
