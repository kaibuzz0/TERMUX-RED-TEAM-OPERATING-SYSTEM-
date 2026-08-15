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
