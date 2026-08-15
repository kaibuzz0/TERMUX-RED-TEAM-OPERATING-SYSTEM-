"""Tests for unified Operations Center views."""

from __future__ import annotations

from pathlib import Path

from operations_center.collectors import Collector


def _collector(tmp_path: Path) -> Collector:
    return Collector(tmp_path / "state", tmp_path / "logs", source_timeout=2.0)


def test_overview_includes_network_services_diagnostics_logs_termux(tmp_path):
    c = _collector(tmp_path)
    overview = c.collect_overview()
    data = overview.get("data", {})
    assert "network" in data
    assert "logs" in data
    assert "termux" in data
    assert "service_total" in data
