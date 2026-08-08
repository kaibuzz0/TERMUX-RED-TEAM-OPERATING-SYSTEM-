"""Milestone 19 — Output / error size boundedness audit.

Production output/error size bounds catalog:
- plugin_sdk.broker_client.PluginClient.request() — MAX_RESULT_SIZE = 256 KiB enforced
  against str(raw) length; raises PluginExecutionError if exceeded.
- plugin_sdk.schema.MAX_STDOUT_SIZE = 64 KiB — schema constant only; NO production enforcement.
- plugin_sdk.schema.MAX_STDERR_SIZE = 64 KiB — schema constant only; NO production enforcement.
- services.process.TrackedProcess — stdout/stderr redirected to subprocess.DEVNULL by default.
  If manifest specifies log targets, supervisor opens them for append; file size unbounded.
- hive_broker.adapters.call_adapter() — captures stdout/stderr into StringIO; no size limit.
- hive_broker.adapters.call_update_adapter/recovery_adapter() — captures stdout/stderr
  from subprocess.run(); no size limit.
- All CLI modules print to stderr without bound.
"""

from __future__ import annotations

import inspect
import io
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. MAX_RESULT_SIZE in broker_client (enforced)
# ---------------------------------------------------------------------------

class TestBrokerResultSizeBounded:
    def test_result_within_limit_accepted(self):
        """Broker result well under MAX_RESULT_SIZE is accepted."""
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.schema import MAX_RESULT_SIZE
        identity = PluginIdentity(
            plugin_id="test",
            plugin_version="1.0.0",
            manifest_digest="sha256:" + "a" * 64,
            installation_id="install-1",
        )
        small_data = {"payload": "x" * 100}
        client = PluginClient(
            identity=identity,
            granted_capabilities=["read"],
            backend=lambda cap, ctx: {"status": "ok", "data": small_data},
        )
        result = client.request("read")
        assert result.status == "ok"

    def test_result_exceeding_limit_rejected(self):
        """Broker result exceeding MAX_RESULT_SIZE raises PluginExecutionError."""
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.schema import MAX_RESULT_SIZE
        from plugin_sdk.errors import PluginExecutionError
        identity = PluginIdentity(
            plugin_id="test",
            plugin_version="1.0.0",
            manifest_digest="sha256:" + "a" * 64,
            installation_id="install-1",
        )
        big_data = {"payload": "x" * (MAX_RESULT_SIZE + 100)}
        client = PluginClient(
            identity=identity,
            granted_capabilities=["read"],
            backend=lambda cap, ctx: {"status": "ok", "data": big_data},
        )
        with pytest.raises(PluginExecutionError, match="exceeded size limit"):
            client.request("read")


# ---------------------------------------------------------------------------
# 2. MAX_STDOUT_SIZE / MAX_STDERR_SIZE — schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestMaxStdoutStderrSchemaOnly:
    def test_constants_defined(self):
        """MAX_STDOUT_SIZE and MAX_STDERR_SIZE are defined in plugin_sdk.schema."""
        from plugin_sdk.schema import MAX_STDOUT_SIZE, MAX_STDERR_SIZE
        assert MAX_STDOUT_SIZE == 64 * 1024
        assert MAX_STDERR_SIZE == 64 * 1024

    def test_no_production_code_enforces_max_stdout(self):
        """No production module reads MAX_STDOUT_SIZE to limit stdout."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_STDOUT_SIZE" in inspect.getsource(s)
        import plugin_sdk.broker_client as bc
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(bc)
        import services.process as sp
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(sp)
        import hive_broker.adapters as ha
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(ha)

    def test_no_production_code_enforces_max_stderr(self):
        """No production module reads MAX_STDERR_SIZE to limit stderr."""
        import inspect
        from plugin_sdk import schema as s
        assert "MAX_STDERR_SIZE" in inspect.getsource(s)
        import plugin_sdk.broker_client as bc
        assert "MAX_STDERR_SIZE" not in inspect.getsource(bc)
        import services.process as sp
        assert "MAX_STDERR_SIZE" not in inspect.getsource(sp)
        import hive_broker.adapters as ha
        assert "MAX_STDERR_SIZE" not in inspect.getsource(ha)


# ---------------------------------------------------------------------------
# 3. services.process stdout/stderr — DEVNULL default, log files unbounded
# ---------------------------------------------------------------------------

class TestTrackedProcessOutputUnbounded:
    def test_default_redirects_to_devnull(self):
        """TrackedProcess.start() redirects stdout and stderr to DEVNULL by default."""
        import inspect
        from services.process import TrackedProcess
        src = inspect.getsource(TrackedProcess.start)
        assert "DEVNULL" in src

    def test_supervisor_log_files_unbounded(self, tmp_path):
        """If manifest specifies stdout/stderr log targets under logging key, supervisor opens them for append."""
        from services.logging import resolve_log_targets
        log_root = tmp_path / "logs"
        manifest = {
            "command": ["echo", "hello"],
            "logging": {
                "stdout": "svc.out",
                "stderr": "svc.err",
            },
        }
        stdout, stderr = resolve_log_targets(manifest, log_root)
        assert stdout is not None
        assert stderr is not None
        # These paths are opened in append mode; file size is unbounded

    def _resolve_log_targets(self, name: str):
        from services.logging import resolve_log_targets
        from services.supervisor import Supervisor
        # Not a real method; helper for test logic
        pass


# ---------------------------------------------------------------------------
# 4. hive_broker.adapters — captures stdout/stderr without size limit
# ---------------------------------------------------------------------------

class TestBrokerAdaptersOutputUnbounded:
    def test_run_services_argv_captures_stdout_no_limit(self):
        """_run_services_argv redirects stdout to StringIO with no explicit size cap."""
        import inspect
        from hive_broker.adapters import _run_services_argv
        src = inspect.getsource(_run_services_argv)
        assert "StringIO()" in src
        assert "MAX" not in src
        assert "limit" not in src.lower()

    def test_run_update_argv_captures_stdout_no_limit(self):
        """_run_update_argv captures subprocess stdout with no size cap."""
        import inspect
        from hive_broker.adapters import _run_update_argv
        src = inspect.getsource(_run_update_argv)
        assert "stdout" in src
        assert "MAX" not in src

    def test_run_recovery_argv_captures_stdout_no_limit(self):
        """_run_recovery_argv captures subprocess stdout with no size cap."""
        import inspect
        from hive_broker.adapters import _run_recovery_argv
        src = inspect.getsource(_run_recovery_argv)
        assert "stdout" in src
        assert "MAX" not in src


# ---------------------------------------------------------------------------
# 5. CLI stderr output — unbounded
# ---------------------------------------------------------------------------

class TestCliStderrUnbounded:
    def test_cli_prints_to_stderr_no_limit(self):
        """CLI modules print error messages to stderr without truncation."""
        import inspect
        from config_engine.cli import cmd_history
        src = inspect.getsource(cmd_history)
        assert "stderr" in src or "print" in src

    def test_no_cli_truncates_error_messages(self):
        """No CLI module truncates error output before printing."""
        import inspect
        from config_engine.cli import cmd_rollback
        src = inspect.getsource(cmd_rollback)
        assert "stderr" in src
        assert "[:" not in src  # no string slicing / truncation pattern


# ---------------------------------------------------------------------------
# 6. Default values
# ---------------------------------------------------------------------------

class TestOutputSizeDefaults:
    def test_max_result_size_default_is_256_kib(self):
        """MAX_RESULT_SIZE default is 256 KiB."""
        from plugin_sdk.schema import MAX_RESULT_SIZE
        assert MAX_RESULT_SIZE == 256 * 1024

    def test_max_stdout_size_default_is_64_kib(self):
        """MAX_STDOUT_SIZE default is 64 KiB."""
        from plugin_sdk.schema import MAX_STDOUT_SIZE
        assert MAX_STDOUT_SIZE == 64 * 1024

    def test_max_stderr_size_default_is_64_kib(self):
        """MAX_STDERR_SIZE default is 64 KiB."""
        from plugin_sdk.schema import MAX_STDERR_SIZE
        assert MAX_STDERR_SIZE == 64 * 1024