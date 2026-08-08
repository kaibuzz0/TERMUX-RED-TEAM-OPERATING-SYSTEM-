"""C5-SDK: Plugin SDK does not reference dispatcher internals.

The plugin SDK is a bounded, manifest-driven API. It does not import or reference
dispatcher internals (Broker.run, adapters, _run_*_argv, etc.) as an architectural
choice — not because Python module imports provide a security boundary.

Python modules can always import each other. The broker's actual security
boundary is policy validation before adapter dispatch (Broker.run), not import-time
separation.

This test verifies the SDK's source-level separation from the broker's execution
surface. It does NOT claim a sandbox where none exists.
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

from plugin_sdk import (
    PluginError,
    PluginCapabilityError,
    PluginIdentity,
    digest_capability_grant,
    load_manifest,
    manifest_digest,
    SDK_VERSION,
    SCHEMA_VERSION,
)


class TestSdkDoesNotReferenceDispatcherInternals:
    """Plugin SDK does not reference broker dispatcher internals.
    
    This is an architectural design choice, not a sandbox boundary.
    Python modules can always import each other.
    The broker's security boundary is policy validation before dispatch.
    """

    # ------------------------------------------------------------------
    # Package exports
    # ------------------------------------------------------------------

    def test_sdk_exports_are_bounded(self):
        """plugin_sdk.__all__ contains only metadata/identity/error types."""
        import plugin_sdk
        exports = set(plugin_sdk.__all__)
        assert "PluginIdentity" in exports
        assert "load_manifest" in exports
        assert "manifest_digest" in exports
        # No dispatcher internals
        assert "PluginClient" not in exports  # present in broker_client but not __all__
        assert "dispatch" not in exports
        assert "Broker" not in exports

    def test_sdk_exports_no_broker_or_dispatcher(self):
        """plugin_sdk package does not export Broker, dispatch, adapters."""
        import plugin_sdk
        names = set(dir(plugin_sdk))
        forbidden = {"Broker", "dispatch", "_dispatch_service", "_run_services_argv",
                     "_run_update_argv", "_run_recovery_argv", "Dispatcher"}
        for name in forbidden:
            assert name not in names, f"Forbidden name {name} exported by plugin_sdk"

    # ------------------------------------------------------------------
    # No broker imports in any plugin_sdk module
    # ------------------------------------------------------------------

    def test_no_hive_broker_imports_in_sdk(self):
        """No plugin_sdk module imports hive_broker (the dispatcher package)."""
        sdk_dir = Path(__file__).parent.parent / "plugin_sdk"
        for py_file in sdk_dir.glob("*.py"):
            src = py_file.read_text()
            assert "import hive_broker" not in src, (
                f"{py_file.name} imports hive_broker"
            )
            assert "from hive_broker" not in src, (
                f"{py_file.name} imports from hive_broker"
            )

    def test_no_dispatcher_references_in_sdk_source(self):
        """No plugin_sdk source file references dispatcher execution internals."""
        sdk_dir = Path(__file__).parent.parent / "plugin_sdk"
        forbidden = {
            "Broker.run", "dispatch(", "_dispatch_service",
            "_run_services_argv", "_run_update_argv", "_run_recovery_argv",
            "importlib", "__import__", "runpy", "exec(", "eval(",
        }
        for py_file in sdk_dir.glob("*.py"):
            src = py_file.read_text()
            for term in forbidden:
                assert term not in src, (
                    f"Forbidden term {term!r} in {py_file.name}"
                )
            # compile( is forbidden only if not re.compile(
            for line in src.splitlines():
                if "compile(" in line and "re.compile(" not in line:
                    assert False, f"Forbidden bare compile() in {py_file.name}: {line.strip()}"

    # ------------------------------------------------------------------
    # AST scan: no exec/eval/importlib in plugin_sdk
    # ------------------------------------------------------------------

    def test_ast_no_exec_eval_in_plugin_sdk(self):
        """Static AST scan confirms no exec/eval/compile in plugin_sdk."""
        sdk_dir = Path(__file__).parent.parent / "plugin_sdk"
        for py_file in sdk_dir.glob("*.py"):
            src = py_file.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        assert node.func.id not in ("exec", "eval", "compile"), (
                            f"Forbidden function {node.func.id} in {py_file.name}"
                        )

    def test_ast_no_importlib_in_plugin_sdk(self):
        """AST scan confirms no importlib/__import__ in plugin_sdk."""
        sdk_dir = Path(__file__).parent.parent / "plugin_sdk"
        for py_file in sdk_dir.glob("*.py"):
            src = py_file.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "importlib" not in alias.name, (
                            f"importlib import in {py_file.name}"
                        )
                if isinstance(node, ast.ImportFrom):
                    if node.module and "importlib" in node.module:
                        assert False, f"importlib import in {py_file.name}"

    # ------------------------------------------------------------------
    # PluginClient boundaries
    # ------------------------------------------------------------------

    def test_plugin_client_rejects_ungranted_capability(self):
        """PluginClient.request raises PluginCapabilityError for ungranted caps."""
        from plugin_sdk.broker_client import PluginClient
        identity = PluginIdentity(
            "test-plugin", "1.0.0",
            manifest_digest="a" * 64,
            installation_id="inst-1",
        )
        client = PluginClient(identity, granted_capabilities=["service.status"])
        # Granted capability accepted
        result = client.request("service.status")
        assert result.policy_decision == "ALLOW"
        # Ungranted capability rejected
        with pytest.raises(PluginCapabilityError):
            client.request("service.start")

    def test_plugin_client_has_no_backend_by_default(self):
        """PluginClient default backend is None — no implicit broker connection."""
        from plugin_sdk.broker_client import PluginClient
        identity = PluginIdentity(
            "test-plugin", "1.0.0",
            manifest_digest="a" * 64,
            installation_id="inst-1",
        )
        client = PluginClient(identity, granted_capabilities=["service.status"])
        assert client.backend is None

    def test_plugin_client_backend_is_optional_callable(self):
        """PluginClient.backend is an optional callable, not a Broker reference."""
        from plugin_sdk.broker_client import PluginClient
        identity = PluginIdentity(
            "test-plugin", "1.0.0",
            manifest_digest="a" * 64,
            installation_id="inst-1",
        )
        def fake_backend(cap, ctx):
            return {"status": "ok"}
        client = PluginClient(identity, granted_capabilities=["service.status"], backend=fake_backend)
        assert callable(client.backend)
        assert client.backend is not None
        result = client.request("service.status")
        assert result.transaction_id  # Has a generated UUID
        assert result.policy_decision == "ALLOW"
        assert result.status == "ok"

    def test_plugin_client_result_size_bounded(self):
        """MAX_RESULT_SIZE is enforced in broker_client source."""
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.schema import MAX_RESULT_SIZE
        identity = PluginIdentity(
            "test-plugin", "1.0.0",
            manifest_digest="a" * 64,
            installation_id="inst-1",
        )
        client = PluginClient(identity, granted_capabilities=["service.status"])
        assert MAX_RESULT_SIZE == 262144  # 256 KiB
        src = inspect.getsource(PluginClient.request)
        assert "MAX_RESULT_SIZE" in src

    # ------------------------------------------------------------------
    # No subprocess/system in plugin_sdk
    # ------------------------------------------------------------------

    def test_no_subprocess_in_plugin_sdk(self):
        """No plugin_sdk module uses subprocess execution primitives."""
        sdk_dir = Path(__file__).parent.parent / "plugin_sdk"
        for py_file in sdk_dir.glob("*.py"):
            src = py_file.read_text()
            # Check for actual subprocess calls, not docstrings
            lines = src.splitlines()
            for line in lines:
                stripped = line.strip()
                # Skip comments/docstrings
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                # Only flag actual subprocess usage (import, run, call, Popen)
                assert "import subprocess" not in line, f"import subprocess in {py_file.name}"
                assert "subprocess.run" not in line, f"subprocess.run in {py_file.name}"
                assert "subprocess.call" not in line, f"subprocess.call in {py_file.name}"
                assert "subprocess.Popen" not in line, f"subprocess.Popen in {py_file.name}"
                assert "os.system" not in line, f"os.system in {py_file.name}"
                assert "os.spawn" not in line, f"os.spawn in {py_file.name}"

    # ------------------------------------------------------------------
    # Plugin policy evaluation is separate from broker policy
    # ------------------------------------------------------------------

    def test_plugin_policy_uses_local_evaluator(self):
        """evaluate_plugin_capability imports from plugin_sdk.policy, not hive_broker.policy."""
        import plugin_sdk.policy as policy_module
        src = inspect.getsource(policy_module)
        assert "hive_broker" not in src
        assert "policy_engine" in src  # uses policy_engine directly (shared)
