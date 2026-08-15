"""Tests for Orbot adapter."""

from __future__ import annotations

from network.orbot import OrbotAdapter, OrbotEndpoints


def test_orbot_socks_unreachable_in_tests():
    adapter = OrbotAdapter(OrbotEndpoints("127.0.0.1", 9050))
    health = adapter.health()
    assert not health["socks_reachable"]


def test_orbot_not_usable_when_socks_down():
    adapter = OrbotAdapter(OrbotEndpoints("127.0.0.1", 9050))
    ok, detail = adapter.usable()
    assert not ok
    assert "not reachable" in detail


def test_orbot_ui_launcher_unavailable_on_windows():
    from network.orbot import _can_launch_activity
    assert not _can_launch_activity()
