"""Tests for `hive audit` read-only guarantee."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from diagnostics import run_audit
from diagnostics.audit import audit_filesystem
from network import NetworkManager
from services.supervisor import Supervisor


def _snapshot(dir_path: Path) -> dict[str, int]:
    """Snapshot mtime for relevant files to detect mutation."""
    snaps = {}
    for p in dir_path.rglob("*"):
        if p.exists():
            snaps[str(p)] = p.stat().st_mtime_ns
    return snaps


def _semantic_snapshot(net_mgr, sup, autoboot_path: Path | None = None):
    snap = {
        "profile": net_mgr.current_profile.name,
        "state": net_mgr.state.to_dict(),
        "services": {},
        "autoboot": None,
    }
    for name in sup.manifests:
        status = sup.status(name)
        snap["services"][name] = {
            "state": status.get("state"),
            "restart_count": status.get("restart_count"),
            "pid": status.get("pid"),
        }
    if autoboot_path is not None and autoboot_path.exists():
        snap["autoboot"] = autoboot_path.read_text(encoding="utf-8")
    return snap


def test_audit_does_not_mutate_state(tmp_path):
    from services.registry import ServiceRegistry
    from services.supervisor import Supervisor
    from config_engine import get_config
    net_mgr = NetworkManager(state_root=tmp_path / "net")
    net_mgr.select_direct()
    registry = ServiceRegistry(tmp_path, tmp_path / "svc_state")
    registry.load([])
    sup = Supervisor(registry.native, tmp_path / "svc_state", tmp_path / "logs", {}, network_manager=net_mgr)
    before_fs = _snapshot(tmp_path)
    before_sem = _semantic_snapshot(net_mgr, sup, tmp_path / "autoboot.txt")
    run_audit(net_mgr, sup, tmp_path, tmp_path / "state", tmp_path / "logs")
    after_fs = _snapshot(tmp_path)
    after_sem = _semantic_snapshot(net_mgr, sup, tmp_path / "autoboot.txt")
    assert before_fs == after_fs, "audit mutated filesystem state"
    assert before_sem == after_sem, "audit mutated semantic runtime state"


def test_audit_finds_bad_permission(tmp_path):
    bad_dir = tmp_path / "state"
    bad_dir.mkdir()
    if os.name == "posix":
        bad_dir.chmod(0o755)
        findings = audit_filesystem(bad_dir, tmp_path / "logs", tmp_path)
        assert any(f.code == "A-FS-001" for f in findings)
        bad_dir.chmod(0o700)
