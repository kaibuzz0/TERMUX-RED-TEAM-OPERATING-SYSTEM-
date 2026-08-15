"""Tests for network profile model and state transitions."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from network.errors import ProfileTransitionError, TorNotAvailableError
from network.manager import NetworkManager
from network.profiles import NetworkProfile


@pytest.fixture
def mgr(tmp_path):
    state_root = tmp_path / "state"
    return NetworkManager(state_root=state_root)


def test_default_profile_is_hold(mgr):
    assert mgr.current_profile == NetworkProfile.HOLD


def test_select_direct(mgr):
    state = mgr.select_direct()
    assert state.profile == "direct"
    assert mgr.current_profile == NetworkProfile.DIRECT


def test_select_hold(mgr):
    mgr.select_direct()
    state = mgr.select_hold()
    assert state.profile == "hold"


def test_select_orbot(mgr):
    state = mgr.select_orbot()
    assert state.profile == "orbot"
    assert state.last_error is not None  # no Orbot in test environment


def test_select_tor_without_binary_fails(mgr):
    with pytest.raises((TorNotAvailableError, ProfileTransitionError)):
        mgr.select_tor()
    assert mgr.current_profile == NetworkProfile.TOR


def test_local_alias_maps_to_tor(mgr):
    from network.profiles import NetworkProfile
    assert NetworkProfile.from_name("local") == NetworkProfile.TOR


def test_off_alias_maps_to_hold(mgr):
    from network.profiles import NetworkProfile
    assert NetworkProfile.from_name("off") == NetworkProfile.HOLD


def test_invalid_profile_raises(mgr):
    with pytest.raises(ValueError):
        NetworkProfile.from_name("does-not-exist")


def test_state_persistence(tmp_path):
    state_root = tmp_path / "state"
    mgr = NetworkManager(state_root=state_root)
    mgr.select_direct()

    # Fresh manager should load persisted state
    mgr2 = NetworkManager(state_root=state_root)
    assert mgr2.current_profile == NetworkProfile.DIRECT
