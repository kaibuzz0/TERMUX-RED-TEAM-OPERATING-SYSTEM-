"""Tests for Hive Home operator landing UI."""

from __future__ import annotations

from pathlib import Path

from home.renderer import render
from home.view_model import HiveHomeState, build_home_state


def test_renderer_healthy_state():
    state = HiveHomeState(
        runtime="ONLINE",
        supervisor="HEALTHY",
        network_profile="TOR",
        tor_health="HEALTHY",
        services="3/3 RUNNING",
        policy="ENFORCED",
        broker="AVAILABLE",
        vault="LOCKED",
        trust="VERIFIED",
        termux="INTEGRATED",
    )
    text = render(state)
    assert "TOR" in text
    assert "HEALTHY" in text
    assert "3/3 RUNNING" in text
    assert "[2] Network" in text


def test_renderer_degraded_network():
    state = HiveHomeState(
        network_profile="TOR",
        tor_health="DEGRADED",
        services="2/3 RUNNING / 1 BLOCKED",
    )
    text = render(state)
    assert "DEGRADED" in text
    assert "BLOCKED" in text


def test_renderer_no_fake_active():
    state = HiveHomeState(tor_health="OFF")
    text = render(state)
    assert "ACTIVE" not in text


def test_build_home_state_does_not_crash(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv("HIVE_STATE_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv("HIVE_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("HIVE_SERVICE_STATE_ROOT", str(tmp_path / "svc_state"))
    monkeypatch.setenv("HIVE_SERVICE_LOG_ROOT", str(tmp_path / "logs"))
    # Build a fake repo root with bin/hive.
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    (repo / "bin" / "hive").write_text("# stub", encoding="utf-8")
    state = build_home_state(repo)
    assert state.network_profile in {"DIRECT", "ORBOT", "TOR", "HOLD", "unknown", "ERROR"}
