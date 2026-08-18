"""Tests for restart policy and crash-loop detection."""

from __future__ import annotations

import time

import pytest

from services.errors import ServiceRuntimeError
from services.restart import RestartPolicy


def test_never_policy_does_not_restart():
    policy = RestartPolicy({"restart": {"policy": "never"}})
    should, delay = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    assert not should


def test_on_failure_restarts_after_nonzero_exit():
    policy = RestartPolicy({"restart": {"policy": "on-failure", "max_attempts": 3, "window_seconds": 60, "backoff_initial_seconds": 1, "backoff_max_seconds": 10}})
    should, delay = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    assert should


def test_on_failure_ignores_success_exit():
    policy = RestartPolicy({"restart": {"policy": "on-failure"}})
    should, _ = policy.should_restart("svc", exit_code=0, manually_stopped=False)
    assert not should


def test_manual_stop_prevents_restart():
    policy = RestartPolicy({"restart": {"policy": "always"}})
    should, _ = policy.should_restart("svc", exit_code=1, manually_stopped=True)
    assert not should


def test_crash_loop_raises_after_max_attempts():
    policy = RestartPolicy({
        "restart": {
            "policy": "always",
            "max_attempts": 2,
            "window_seconds": 60,
            "backoff_initial_seconds": 1,
            "backoff_max_seconds": 10,
        }
    })
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    with pytest.raises(ServiceRuntimeError):
        policy.should_restart("svc", exit_code=1, manually_stopped=False)


def test_backoff_grows():
    policy = RestartPolicy({
        "restart": {
            "policy": "always",
            "max_attempts": 5,
            "window_seconds": 60,
            "backoff_initial_seconds": 1,
            "backoff_max_seconds": 10,
        }
    })
    _, d1 = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.states["svc"].attempts = 0
    _, d2 = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.states["svc"].attempts = 2
    _, d3 = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    assert d2 < d3



def test_zero_window_enforces_crash_loop_within_burst():
    """window_seconds=0 disables reset so max_attempts caps the same burst."""
    policy = RestartPolicy({
        "restart": {
            "policy": "always",
            "max_attempts": 3,
            "window_seconds": 0,
            "backoff_initial_seconds": 1,
            "backoff_max_seconds": 10,
        }
    })
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    with pytest.raises(ServiceRuntimeError, match="crash loop"):
        policy.should_restart("svc", exit_code=1, manually_stopped=False)


def test_positive_window_resets_attempts_after_elapsed_time(monkeypatch):
    """After window_seconds elapses, attempt counter resets and service may restart again."""
    policy = RestartPolicy({
        "restart": {
            "policy": "always",
            "max_attempts": 2,
            "window_seconds": 5,
            "backoff_initial_seconds": 1,
            "backoff_max_seconds": 10,
        }
    })
    start = 1000.0
    monkeypatch.setattr(time, "time", lambda: start)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    with pytest.raises(ServiceRuntimeError, match="crash loop"):
        policy.should_restart("svc", exit_code=1, manually_stopped=False)
    # Move past the window
    monkeypatch.setattr(time, "time", lambda: start + 6)
    should, _ = policy.should_restart("svc", exit_code=1, manually_stopped=False)
    assert should


def test_mark_success_resets_crash_loop_state():
    """A healthy run resets attempts and crash_loop flag."""
    policy = RestartPolicy({
        "restart": {
            "policy": "always",
            "max_attempts": 2,
            "window_seconds": 0,
            "backoff_initial_seconds": 1,
            "backoff_max_seconds": 10,
        }
    })
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.mark_success("svc")
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    policy.should_restart("svc", exit_code=1, manually_stopped=False)
    with pytest.raises(ServiceRuntimeError, match="crash loop"):
        policy.should_restart("svc", exit_code=1, manually_stopped=False)
