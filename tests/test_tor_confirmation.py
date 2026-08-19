"""Tests for explicit Tor confirmation semantics."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from network import NetworkManager
from network.profiles import NetworkProfile
from network.state import update_profile


@pytest.fixture
def tor_manager(tmp_path):
    update_profile(tmp_path, NetworkProfile.TOR)
    mgr = NetworkManager(state_root=tmp_path)
    mgr._load()
    return mgr


def test_tor_confirmation_false_when_not_tor(tor_manager):
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"IsTor": false, "IP": "1.2.3.4"}'

    with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()):
        ok, detail = tor_manager._tor_confirmation_test()
    assert not ok
    assert "IsTor=false" in detail


def test_tor_confirmation_true_when_tor(tor_manager):
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"IsTor": true, "IP": "185.220.101.42"}'

    with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()):
        ok, detail = tor_manager._tor_confirmation_test()
    assert ok
    assert "Tor confirmed" in detail


def test_tor_confirmation_false_on_malformed_response(tor_manager):
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"not json"

    with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()):
        ok, detail = tor_manager._tor_confirmation_test()
    assert not ok
    assert "non-JSON" in detail
