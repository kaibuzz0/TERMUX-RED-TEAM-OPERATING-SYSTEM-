from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from bootstrap.install_release import install_global_launcher
from installer.activate import ActiveState
from installer.plan import generate_plan
from installer.staging import StagingArea


class _ExecIntercept(RuntimeError):
    def __init__(self, executable: str, argv: list[str]):
        super().__init__(executable)
        self.executable = executable
        self.argv = argv


def _resolved_launcher_entry(launcher: Path, monkeypatch) -> Path:
    """Execute the managed launcher until its final os.execv handoff."""

    def fake_execv(executable: str, argv: list[str]) -> None:
        raise _ExecIntercept(executable, argv)

    monkeypatch.setattr(os, "execv", fake_execv)
    monkeypatch.setattr(sys, "argv", [str(launcher), "status"])
    source = launcher.read_text(encoding="utf-8")
    namespace = {"__name__": "__main__", "__file__": str(launcher)}
    with pytest.raises(_ExecIntercept) as intercepted:
        exec(compile(source, str(launcher), "exec"), namespace, namespace)
    assert intercepted.value.executable == sys.executable
    assert intercepted.value.argv[0] == sys.executable
    assert intercepted.value.argv[-1] == "status"
    return Path(intercepted.value.argv[1]).resolve()


def _promote(state: ActiveState | None, transaction_id: str):
    plan = generate_plan(transaction_id=transaction_id)
    area = StagingArea(plan)
    staged = area.stage_all()
    if state is None:
        state = ActiveState(plan.target.data_root, plan.target.state_root, plan.transaction_id)
    release = state.promote_to_ready(staged, plan)
    return state, release


def test_one_global_launcher_follows_activate_update_and_rollback(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    prefix = tmp_path / "termux-prefix"

    state, release_a = _promote(None, "txn-v2-lifecycle-a")
    pointer_a = state.activate(release_a.release_id, approve=True)
    launcher = install_global_launcher(state.data_root, prefix)
    launcher_bytes = launcher.read_bytes()
    launcher_mode = os.stat(launcher).st_mode & 0o7777

    expected_a = (state.data_root / "releases" / release_a.release_id / "runtime" / "bin" / "hive").resolve()
    assert Path(pointer_a.active_runtime).resolve() == expected_a.parent.parent
    assert _resolved_launcher_entry(launcher, monkeypatch) == expected_a

    state, release_b = _promote(state, "txn-v2-lifecycle-b")
    pointer_b = state.activate(release_b.release_id, approve=True)
    expected_b = (state.data_root / "releases" / release_b.release_id / "runtime" / "bin" / "hive").resolve()

    assert pointer_b.active_release_id == release_b.release_id
    assert pointer_b.previous_release_id == release_a.release_id
    assert launcher.read_bytes() == launcher_bytes
    assert os.stat(launcher).st_mode & 0o7777 == launcher_mode
    assert _resolved_launcher_entry(launcher, monkeypatch) == expected_b

    rolled_back = state.rollback(approve=True)
    assert rolled_back.active_release_id == release_a.release_id
    assert rolled_back.previous_release_id == release_b.release_id
    assert launcher.read_bytes() == launcher_bytes
    assert os.stat(launcher).st_mode & 0o7777 == launcher_mode
    assert _resolved_launcher_entry(launcher, monkeypatch) == expected_a
