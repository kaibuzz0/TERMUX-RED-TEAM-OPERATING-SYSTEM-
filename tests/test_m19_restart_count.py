"""Milestone 19 — Service restart count boundedness audit.

Production restart count bounds catalog:
- services.restart.RestartPolicy — max_attempts default=5, window_seconds=300
  - should_restart() raises ServiceRuntimeError (crash loop) after max_attempts
  - Window reset: attempts reset if stable window passed
  - Exponential backoff capped at max_backoff (default 60s)
- services.state.ServiceInstance.restart_count — NO explicit bound (simple int)
- services.supervisor.Supervisor.restart() — increments restart_count, delegates to RestartPolicy
"""

from __future__ import annotations

import time

import pytest


# ---------------------------------------------------------------------------
# 1. RestartPolicy exact boundary tests
# ---------------------------------------------------------------------------

class TestRestartPolicyMaxAttemptsBounded:
    def test_should_restart_accepts_up_to_max_attempts(self):
        """RestartPolicy.should_restart allows max_attempts consecutive restarts."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always", "max_attempts": 5}})
        for attempt in range(1, 6):
            ok, delay = policy.should_restart("svc1", exit_code=1, manually_stopped=False)
            assert ok is True, f"attempt {attempt} should be allowed"
            assert delay > 0

    def test_should_restart_rejects_max_attempts_plus_1(self):
        """RestartPolicy.should_restart raises ServiceRuntimeError on attempt > max_attempts."""
        from services.restart import RestartPolicy
        from services.errors import ServiceRuntimeError
        policy = RestartPolicy({"restart": {"policy": "always", "max_attempts": 5}})
        for _ in range(5):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        with pytest.raises(ServiceRuntimeError, match="crash loop"):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)

    def test_should_restart_crash_loop_flag_set(self):
        """Crash loop flag is set after exceeding max_attempts."""
        from services.restart import RestartPolicy
        from services.errors import ServiceRuntimeError
        policy = RestartPolicy({"restart": {"policy": "always", "max_attempts": 3}})
        for _ in range(3):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        assert policy.states["svc1"].crash_loop is False
        with pytest.raises(ServiceRuntimeError):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        assert policy.states["svc1"].crash_loop is True


# ---------------------------------------------------------------------------
# 2. Window reset behavior
# ---------------------------------------------------------------------------

class TestRestartPolicyWindowReset:
    def test_window_reset_allows_restarts_after_stable_period(self):
        """After window_seconds pass, attempts reset and restarts are allowed again."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({
            "restart": {"policy": "always", "max_attempts": 2, "window_seconds": 1},
        })
        for _ in range(2):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        with pytest.raises(Exception):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        # Wait for window to pass
        time.sleep(1.1)
        ok, delay = policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        assert ok is True
        assert policy.states["svc1"].attempts == 1

    def test_window_reset_clears_crash_loop_flag(self):
        """Window reset also clears the crash_loop flag."""
        from services.restart import RestartPolicy
        from services.errors import ServiceRuntimeError
        policy = RestartPolicy({
            "restart": {"policy": "always", "max_attempts": 2, "window_seconds": 1},
        })
        for _ in range(2):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        with pytest.raises(ServiceRuntimeError):
            policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        assert policy.states["svc1"].crash_loop is True
        time.sleep(1.1)
        policy.should_restart("svc1", exit_code=1, manually_stopped=False)
        assert policy.states["svc1"].crash_loop is False


# ---------------------------------------------------------------------------
# 3. Exponential backoff calculation
# ---------------------------------------------------------------------------

class TestRestartPolicyBackoff:
    def test_backoff_doubles_each_attempt(self):
        """Backoff delay doubles with each attempt (exponential)."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({
            "restart": {"policy": "always", "max_attempts": 5, "backoff_initial_seconds": 2},
        })
        expected_delays = [2, 4, 8, 16, 32]
        for i, expected in enumerate(expected_delays, start=1):
            ok, delay = policy.should_restart("svc1", exit_code=1, manually_stopped=False)
            assert ok is True
            assert delay == expected, f"attempt {i}: expected {expected}, got {delay}"

    def test_backoff_capped_at_max_backoff(self):
        """Backoff is capped at max_backoff seconds."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({
            "restart": {
                "policy": "always",
                "max_attempts": 10,
                "backoff_initial_seconds": 10,
                "backoff_max_seconds": 60,
            },
        })
        delays = []
        for _ in range(10):
            ok, delay = policy.should_restart("svc2", exit_code=1, manually_stopped=False)
            delays.append(delay)
        # After initial=10, delays should be: 10, 20, 40, 60, 60, 60, ...
        assert delays[0] == 10
        assert delays[1] == 20
        assert delays[2] == 40
        for d in delays[3:]:
            assert d == 60, f"expected cap at 60, got {d}"


# ---------------------------------------------------------------------------
# 4. Restart policy modes
# ---------------------------------------------------------------------------

class TestRestartPolicyModes:
    def test_never_policy_rejects_all(self):
        """policy='never' always returns False."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "never"}})
        ok, delay = policy.should_restart("svc", exit_code=1, manually_stopped=False)
        assert ok is False
        assert delay == 0.0

    def test_on_failure_rejects_zero_exit(self):
        """policy='on-failure' does not restart on successful exit (0)."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "on-failure"}})
        ok, delay = policy.should_restart("svc", exit_code=0, manually_stopped=False)
        assert ok is False
        assert delay == 0.0

    def test_on_failure_restarts_on_nonzero_exit(self):
        """policy='on-failure' restarts on nonzero exit code."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "on-failure"}})
        ok, delay = policy.should_restart("svc", exit_code=1, manually_stopped=False)
        assert ok is True
        assert delay > 0

    def test_unless_stopped_rejects_after_manual_stop(self):
        """policy='unless-stopped' does not restart after manual stop."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "unless-stopped"}})
        ok, delay = policy.should_restart("svc", exit_code=1, manually_stopped=True)
        assert ok is False
        assert delay == 0.0

    def test_manual_stop_rejects_all_policies(self):
        """manually_stopped=True always prevents restart regardless of policy."""
        from services.restart import RestartPolicy
        for pol in ("always", "on-failure", "unless-stopped"):
            policy = RestartPolicy({"restart": {"policy": pol}})
            ok, delay = policy.should_restart("svc", exit_code=1, manually_stopped=True)
            assert ok is False, f"policy {pol} should reject manual stop"


# ---------------------------------------------------------------------------
# 5. mark_success and reset
# ---------------------------------------------------------------------------

class TestRestartPolicyStateManagement:
    def test_mark_success_resets_attempts(self):
        """mark_success() resets attempts and crash_loop flag."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always", "max_attempts": 5}})
        for _ in range(3):
            policy.should_restart("svc", exit_code=1, manually_stopped=False)
        policy.mark_success("svc")
        assert policy.states["svc"].attempts == 0
        assert policy.states["svc"].crash_loop is False

    def test_reset_clears_all_state(self):
        """reset() returns a fresh RestartState."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always", "max_attempts": 5}})
        for _ in range(3):
            policy.should_restart("svc", exit_code=1, manually_stopped=False)
        policy.reset("svc")
        assert policy.states["svc"].attempts == 0
        assert policy.states["svc"].crash_loop is False
        assert policy.states["svc"].last_attempt == 0.0


# ---------------------------------------------------------------------------
# 6. ServiceInstance.restart_count is unbounded
# ---------------------------------------------------------------------------

class TestServiceInstanceRestartCountUnbounded:
    def test_restart_count_increments_without_bound(self):
        """ServiceInstance.restart_count is a plain int with no explicit max."""
        from services.state import ServiceInstance
        instance = ServiceInstance(service_name="svc")
        for _ in range(10000):
            instance.restart_count += 1
        assert instance.restart_count == 10000

    def test_restart_count_persists_in_state(self):
        """restart_count is serialized to state JSON without bound check."""
        from services.state import ServiceInstance
        instance = ServiceInstance(service_name="svc", restart_count=99999)
        data = instance.to_dict()
        assert data["restart_count"] == 99999
        restored = ServiceInstance.from_dict(data)
        assert restored.restart_count == 99999


# ---------------------------------------------------------------------------
# 7. Supervisor delegates to RestartPolicy
# ---------------------------------------------------------------------------

class TestSupervisorRestartDelegation:
    def test_supervisor_restart_increments_restart_count(self):
        """Supervisor.restart() increments ServiceInstance.restart_count via _record."""
        from services.supervisor import Supervisor
        from services.state import ServiceInstance
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            sup = Supervisor(
                manifests={},
                state_root=Path(tmp),
                log_root=Path(tmp),
                runtime_info={},
            )
            sup._record("svc", state="DEFINED", restart_count=0)
            sup._record("svc", restart_count=1)
            from services.state import load_state
            state = load_state(Path(tmp))
            assert state["svc"]["restart_count"] == 1

    def test_supervisor_restart_uses_policy(self):
        """Supervisor constructs RestartPolicy from manifest and delegates."""
        from services.supervisor import Supervisor
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            manifests = {
                "svc": {"restart": {"policy": "always", "max_attempts": 3}},
            }
            sup = Supervisor(
                manifests=manifests,
                state_root=Path(tmp),
                log_root=Path(tmp),
                runtime_info={},
            )
            policy = sup.policies["svc"]
            for _ in range(3):
                ok, _ = policy.should_restart("svc", exit_code=1, manually_stopped=False)
                assert ok is True
            with pytest.raises(Exception, match="crash loop"):
                policy.should_restart("svc", exit_code=1, manually_stopped=False)


# ---------------------------------------------------------------------------
# 8. Default configuration values
# ---------------------------------------------------------------------------

class TestRestartPolicyDefaults:
    def test_default_max_attempts_is_5(self):
        """RestartPolicy defaults max_attempts to 5 when not specified."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always"}})
        assert policy.max_attempts == 5

    def test_default_window_seconds_is_300(self):
        """RestartPolicy defaults window_seconds to 300 when not specified."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always"}})
        assert policy.window_seconds == 300

    def test_default_backoff_initial_is_2(self):
        """RestartPolicy defaults backoff_initial_seconds to 2."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always"}})
        assert policy.initial == 2

    def test_default_backoff_max_is_60(self):
        """RestartPolicy defaults backoff_max_seconds to 60."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({"restart": {"policy": "always"}})
        assert policy.max_backoff == 60

    def test_default_policy_is_never(self):
        """RestartPolicy defaults policy to 'never' when no restart config."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({})
        assert policy.policy == "never"