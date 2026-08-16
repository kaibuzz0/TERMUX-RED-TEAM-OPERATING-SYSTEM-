"""Milestone 19 — Output / error size boundedness audit.

Production output/error size bounds catalog:
- plugin_sdk.broker_client.PluginClient.request() — MAX_RESULT_SIZE = 256 KiB enforced.
- plugin_sdk.schema.MAX_STDOUT_SIZE / MAX_STDERR_SIZE — schema constants only.
- services.process.TrackedProcess — stdout/stderr redirected to DEVNULL by default.
- hive_broker adapters capture subprocess stdout/stderr without an explicit size cap.
"""

from __future__ import annotations

import inspect

import pytest


class TestBrokerResultSizeBounded:
    def test_result_within_limit_accepted(self):
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.identity import PluginIdentity
        identity = PluginIdentity(
            plugin_id="test", plugin_version="1.0.0",
            manifest_digest="sha256:" + "a" * 64, installation_id="install-1",
        )
        client = PluginClient(
            identity=identity,
            granted_capabilities=["read"],
            backend=lambda cap, ctx: {"status": "ok", "data": {"payload": "x" * 100}},
        )
        assert client.request("read").status == "ok"

    def test_result_exceeding_limit_rejected(self):
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.schema import MAX_RESULT_SIZE
        from plugin_sdk.errors import PluginExecutionError
        identity = PluginIdentity(
            plugin_id="test", plugin_version="1.0.0",
            manifest_digest="sha256:" + "a" * 64, installation_id="install-1",
        )
        client = PluginClient(
            identity=identity,
            granted_capabilities=["read"],
            backend=lambda cap, ctx: {"status": "ok", "data": {"payload": "x" * (MAX_RESULT_SIZE + 100)}},
        )
        with pytest.raises(PluginExecutionError, match="exceeded size limit"):
            client.request("read")


class TestMaxStdoutStderrSchemaOnly:
    def test_constants_defined(self):
        from plugin_sdk.schema import MAX_STDOUT_SIZE, MAX_STDERR_SIZE
        assert MAX_STDOUT_SIZE == 64 * 1024
        assert MAX_STDERR_SIZE == 64 * 1024

    def test_no_production_code_enforces_max_stdout(self):
        from plugin_sdk import schema as s
        import plugin_sdk.broker_client as bc
        import services.process as sp
        import hive_broker.adapters as ha
        assert "MAX_STDOUT_SIZE" in inspect.getsource(s)
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(bc)
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(sp)
        assert "MAX_STDOUT_SIZE" not in inspect.getsource(ha)

    def test_no_production_code_enforces_max_stderr(self):
        from plugin_sdk import schema as s
        import plugin_sdk.broker_client as bc
        import services.process as sp
        import hive_broker.adapters as ha
        assert "MAX_STDERR_SIZE" in inspect.getsource(s)
        assert "MAX_STDERR_SIZE" not in inspect.getsource(bc)
        assert "MAX_STDERR_SIZE" not in inspect.getsource(sp)
        assert "MAX_STDERR_SIZE" not in inspect.getsource(ha)


class TestTrackedProcessOutputUnbounded:
    def test_default_redirects_to_devnull(self):
        from services.process import TrackedProcess
        assert "DEVNULL" in inspect.getsource(TrackedProcess.start)

    def test_supervisor_log_files_unbounded(self, tmp_path):
        from services.logging import resolve_log_targets
        stdout, stderr = resolve_log_targets(
            {"command": ["echo", "hello"], "logging": {"stdout": "svc.out", "stderr": "svc.err"}},
            tmp_path / "logs",
        )
        assert stdout is not None
        assert stderr is not None


class TestBrokerAdaptersOutputUnbounded:
    def test_run_services_argv_captures_stdout_no_limit(self):
        from hive_broker.adapters import _run_services_argv
        src = inspect.getsource(_run_services_argv)
        assert "capture_output=True" in src
        assert "proc.stdout" in src
        assert "proc.stderr" in src
        assert "MAX_STDOUT_SIZE" not in src
        assert "MAX_STDERR_SIZE" not in src

    def test_run_update_argv_captures_stdout_no_limit(self):
        from hive_broker.adapters import _run_update_argv
        src = inspect.getsource(_run_update_argv)
        assert "stdout" in src
        assert "MAX" not in src

    def test_run_recovery_argv_captures_stdout_no_limit(self):
        from hive_broker.adapters import _run_recovery_argv
        src = inspect.getsource(_run_recovery_argv)
        assert "stdout" in src
        assert "MAX" not in src


class TestCliStderrUnbounded:
    def test_cli_prints_to_stderr_no_limit(self):
        from config_engine.cli import cmd_history
        src = inspect.getsource(cmd_history)
        assert "stderr" in src or "print" in src

    def test_no_cli_truncates_error_messages(self):
        from config_engine.cli import cmd_rollback
        src = inspect.getsource(cmd_rollback)
        assert "stderr" in src
        assert "[:" not in src


class TestOutputSizeDefaults:
    def test_max_result_size_default_is_256_kib(self):
        from plugin_sdk.schema import MAX_RESULT_SIZE
        assert MAX_RESULT_SIZE == 256 * 1024

    def test_max_stdout_size_default_is_64_kib(self):
        from plugin_sdk.schema import MAX_STDOUT_SIZE
        assert MAX_STDOUT_SIZE == 64 * 1024

    def test_max_stderr_size_default_is_64_kib(self):
        from plugin_sdk.schema import MAX_STDERR_SIZE
        assert MAX_STDERR_SIZE == 64 * 1024
