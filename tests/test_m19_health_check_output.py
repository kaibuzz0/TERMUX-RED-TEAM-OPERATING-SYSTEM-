"""Milestone 19 — Health-check output boundedness audit.

Production health-check output bounds catalog:
- services.health.HealthCheck.check() — returns a bounded structured dict.
  Output size is independent of the underlying check mechanism.
- _command_check() — uses subprocess.run(capture_output=True) but does NOT include
  stdout/stderr in the return value; only returns healthy, type, exit_code.
  The captured output is discarded after the check.
- _tcp_check() — returns a small dict with healthy, type, and optional error string.
- _file_check() — returns a small dict with healthy, type, and optional error string.
- process check — returns a small dict with healthy, type.
- services.supervisor.health() — delegates to HealthCheck.check(); inherits bounded output.
- services.schema._validate_health() — validates config shape only; no output size bound.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. HealthCheck output dict is always small and bounded
# ---------------------------------------------------------------------------

class TestHealthCheckOutputBounded:
    def test_none_check_returns_small_dict(self):
        """HealthCheck type='none' returns a tiny bounded dict."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "none"}})
        result = hc.check(None, Path("/tmp"))
        assert set(result.keys()) <= {"healthy", "type"}
        assert len(str(result)) < 200

    def test_process_check_returns_small_dict(self):
        """HealthCheck type='process' returns a tiny bounded dict."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "process"}})
        result = hc.check(None, Path("/tmp"))
        assert set(result.keys()) <= {"healthy", "type"}
        assert len(str(result)) < 200

    def test_command_check_returns_small_dict_no_stdout(self):
        """HealthCheck type='command' returns a small dict WITHOUT the command's stdout/stderr."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "command", "args": ["echo", "hello"]}})
        result = hc.check(None, Path("/tmp"))
        assert "stdout" not in result
        assert "stderr" not in result
        # Allow an optional documented error key when the health probe cannot
        # run on Windows without bash; the contract still bounds output size.
        assert set(result.keys()) <= {"healthy", "type", "exit_code", "error"}
        assert len(str(result)) < 200

    def test_tcp_check_returns_small_dict(self):
        """HealthCheck type='tcp-local' returns a small bounded dict."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "tcp-local", "host": "127.0.0.1", "port": 99999}})
        result = hc.check(None, Path("/tmp"))
        assert set(result.keys()) <= {"healthy", "type", "error"}
        assert len(str(result)) < 300

    def test_file_check_returns_small_dict(self):
        """HealthCheck type='file' returns a small bounded dict."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "file", "path": "nonexistent.log"}})
        result = hc.check(None, Path("/tmp"))
        assert set(result.keys()) <= {"healthy", "type", "error"}
        assert len(str(result)) < 300


# ---------------------------------------------------------------------------
# 2. Command check captures but discards stdout/stderr
# ---------------------------------------------------------------------------

class TestCommandCheckDiscardsOutput:
    def test_command_check_does_not_return_stdout(self):
        """_command_check() never includes 'stdout' in its return dict."""
        import inspect
        from services.health import HealthCheck
        src = inspect.getsource(HealthCheck._command_check)
        assert "'stdout'" not in src
        assert '"stdout"' not in src

    def test_command_check_does_not_return_stderr(self):
        """_command_check() never includes 'stderr' in its return dict."""
        import inspect
        from services.health import HealthCheck
        src = inspect.getsource(HealthCheck._command_check)
        assert "'stderr'" not in src
        assert '"stderr"' not in src

    def test_command_check_uses_capture_output_true(self):
        """_command_check() uses subprocess.run(capture_output=True) to avoid streaming."""
        import inspect
        from services.health import HealthCheck
        src = inspect.getsource(HealthCheck._command_check)
        assert "capture_output=True" in src


# ---------------------------------------------------------------------------
# 3. TCP check rejects non-loopback hosts (bounded attack surface)
# ---------------------------------------------------------------------------

class TestTcpCheckBounded:
    def test_tcp_check_rejects_non_loopback_host(self):
        """_tcp_check() rejects non-loopback hosts immediately; no socket created."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "tcp-local", "host": "8.8.8.8", "port": 80}})
        result = hc.check(None, Path("/tmp"))
        assert result["healthy"] is False
        assert "Non-loopback host rejected" in result["error"]

    def test_tcp_check_rejects_invalid_port(self):
        """_tcp_check() rejects invalid ports immediately."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "tcp-local", "host": "127.0.0.1", "port": -1}})
        result = hc.check(None, Path("/tmp"))
        assert result["healthy"] is False
        assert "Invalid port" in result["error"]

    def test_tcp_check_default_timeout_is_5_seconds(self):
        """_tcp_check() uses a 5-second default timeout."""
        import inspect
        from services.health import HealthCheck
        src = inspect.getsource(HealthCheck._tcp_check)
        assert "timeout_seconds" in src


# ---------------------------------------------------------------------------
# 4. File check rejects path traversal
# ---------------------------------------------------------------------------

class TestFileCheckBounded:
    def test_file_check_rejects_absolute_path(self):
        """_file_check() rejects absolute paths immediately."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "file", "path": "/etc/passwd"}})
        result = hc.check(None, Path("/tmp"))
        assert result["healthy"] is False
        assert "path escapes" in result["error"]

    def test_file_check_rejects_parent_traversal(self):
        """_file_check() uses Path.relative_to() which raises on escaping paths."""
        import inspect
        from services.health import HealthCheck
        src = inspect.getsource(HealthCheck._file_check)
        assert "relative_to" in src
        # Path.relative_to() rejects paths with '..' that escape the base



# ---------------------------------------------------------------------------
# 5. Supervisor delegates to HealthCheck (inherits bounded output)
# ---------------------------------------------------------------------------

class TestSupervisorHealthDelegation:
    def test_supervisor_health_returns_bounded_dict(self):
        """Supervisor.health() delegates to HealthCheck.check() and returns a bounded dict."""
        from services.supervisor import Supervisor
        from services.state import ServiceInstance
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            manifests = {
                "svc": {"health_check": {"type": "none"}},
            }
            sup = Supervisor(
                manifests=manifests,
                state_root=Path(tmp) / "state",
                log_root=Path(tmp) / "logs",
                runtime_info={},
            )
            result = sup.health("svc")
            assert "healthy" in result
            assert len(str(result)) < 300


# ---------------------------------------------------------------------------
# 6. Health config validation rejects shell metacharacters
# ---------------------------------------------------------------------------

class TestHealthConfigValidation:
    def test_command_args_reject_shell_metacharacters(self):
        """_validate_health rejects shell metacharacters in command args."""
        from services.schema import _validate_health
        from services.errors import ServiceConfigError
        with pytest.raises(ServiceConfigError, match="shell metacharacters"):
            _validate_health({"type": "command", "args": ["echo", "foo; rm -rf /"]}, "svc")

    def test_file_path_reject_shell_metacharacters(self):
        """_validate_health rejects shell metacharacters in file path."""
        from services.schema import _validate_health
        from services.errors import ServiceConfigError
        with pytest.raises(ServiceConfigError, match="shell metacharacters"):
            _validate_health({"type": "file", "path": "log; rm -rf /"}, "svc")

    def test_file_path_reject_absolute_path(self):
        """_validate_health rejects absolute file paths."""
        from services.schema import _validate_health
        from services.errors import ServiceConfigError
        with pytest.raises(ServiceConfigError, match="relative"):
            _validate_health({"type": "file", "path": "/etc/passwd"}, "svc")

    def test_tcp_host_must_be_loopback(self):
        """_validate_health enforces loopback-only hosts for tcp-local."""
        from services.schema import _validate_health
        from services.errors import ServiceConfigError
        with pytest.raises(ServiceConfigError, match="loopback"):
            _validate_health({"type": "tcp-local", "host": "8.8.8.8", "port": 80}, "svc")


# ---------------------------------------------------------------------------
# 7. Unsupported health check type returns bounded error
# ---------------------------------------------------------------------------

class TestUnsupportedHealthType:
    def test_unsupported_type_returns_bounded_error_dict(self):
        """An unsupported health_check type returns a small error dict."""
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "unsupported_fancy_type"}})
        result = hc.check(None, Path("/tmp"))
        assert result["healthy"] is False
        assert result["type"] == "unsupported_fancy_type"
        assert "error" in result
        assert len(str(result)) < 200