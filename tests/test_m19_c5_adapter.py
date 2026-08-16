"""C5-ADAPTER: Adapter structural verification.

The adapter functions in hive_broker/adapters.py are internal helpers called by
the dispatcher AFTER policy authorization. This test verifies their structural
properties: bounded mappings, fail-closed behavior, and absence of dangerous
patterns.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from hive_broker.adapters import (
    dispatch,
    AdapterError,
    _dispatch_service,
    _dispatch_vault,
    _dispatch_update,
    _dispatch_recovery,
    _run_services_argv,
    _run_update_argv,
    _run_recovery_argv,
)


class TestAdapterStructural:
    """Structural proofs for broker adapters."""

    def test_dispatch_raises_adapter_error_for_unknown_capability(self):
        with pytest.raises(AdapterError) as exc:
            dispatch("unknown.capability", None, {})
        assert "No adapter" in str(exc.value)

    def test_dispatch_raises_for_arbitrary_prefix(self):
        with pytest.raises(AdapterError):
            dispatch("service.evil", None, {})
        with pytest.raises(AdapterError):
            dispatch("vault.secret.read", None, {})
        with pytest.raises(AdapterError):
            dispatch("update.force", None, {})
        with pytest.raises(AdapterError):
            dispatch("recovery.reset", None, {})

    def test_dispatch_returns_for_known_readonly_capabilities(self):
        cap_result = dispatch("broker.capabilities", None, {})
        assert "capabilities" in cap_result
        from hive_broker.transaction import Transaction
        txn = Transaction("txn-test", "task-test", "sess-test", "audit-1")
        status_result = dispatch("broker.status", txn, {})
        assert status_result["status"] == "ok"

    def test_service_adapter_only_maps_readonly_ops(self):
        allowed = {"service.list", "service.show", "service.status",
                   "service.health", "service.validate", "service.graph"}
        for cap in allowed:
            try:
                result = _dispatch_service(cap, {"service": "test"})
                assert isinstance(result, dict)
            except Exception as e:
                assert "AdapterError" not in type(e).__name__

    def test_service_adapter_rejects_mutating_ops(self):
        for cap in ("service.start", "service.stop", "service.restart",
                    "service.kill", "service.remove"):
            with pytest.raises(AdapterError):
                _dispatch_service(cap, {})

    def test_vault_adapter_is_placeholder_only(self):
        result = _dispatch_vault("vault.status", {})
        assert result["status"] == "locked"
        with pytest.raises(AdapterError):
            _dispatch_vault("vault.secret.get", {})
        with pytest.raises(AdapterError):
            _dispatch_vault("vault.secret.read", {})

    def test_update_adapter_bounded(self):
        for cap in ("update.status", "update.inspect", "update.plan", "update.verify"):
            try:
                result = _dispatch_update(cap, {})
                assert isinstance(result, dict)
            except AdapterError:
                pytest.fail(f"AdapterError should not be raised for {cap}")
            except Exception:
                pass

    def test_update_adapter_rejects_apply(self):
        with pytest.raises(AdapterError):
            _dispatch_update("update.apply", {})

    def test_recovery_adapter_bounded(self):
        for cap in ("recovery.status", "recovery.diagnose",
                    "recovery.inspect", "recovery.verify"):
            try:
                result = _dispatch_recovery(cap, {})
                assert isinstance(result, dict)
            except AdapterError:
                pytest.fail(f"AdapterError should not be raised for {cap}")
            except Exception:
                pass

    def test_recovery_adapter_rejects_restore(self):
        with pytest.raises(AdapterError):
            _dispatch_recovery("recovery.restore", {})

    def test_update_argv_uses_shell_false(self):
        src = inspect.getsource(_run_update_argv)
        assert "shell=False" in src
        assert "subprocess.run" in src

    def test_recovery_argv_uses_shell_false(self):
        src = inspect.getsource(_run_recovery_argv)
        assert "shell=False" in src
        assert "subprocess.run" in src

    def test_update_argv_has_timeout(self):
        assert "timeout=" in inspect.getsource(_run_update_argv)

    def test_recovery_argv_has_timeout(self):
        assert "timeout=" in inspect.getsource(_run_recovery_argv)

    def test_services_argv_redirects_stdout_stderr(self):
        """Service CLI output is isolated and captured by subprocess.run."""
        src = inspect.getsource(_run_services_argv)
        assert "subprocess.run" in src
        assert "capture_output=True" in src
        assert '"stdout": proc.stdout' in src
        assert '"stderr": proc.stderr' in src
        assert "shell=False" in src

    def test_no_getattr_in_adapters(self):
        src = inspect.getsource(dispatch)
        assert "getattr" not in src
        assert "eval(" not in src
        assert "exec(" not in src

    def test_no_importlib_in_adapters(self):
        import hive_broker.adapters as adapters_module
        src = inspect.getsource(adapters_module)
        assert "importlib" not in src
        assert "__import__" not in src

    def test_adapter_internals_not_in_hive_broker_exports(self):
        import hive_broker
        public_names = getattr(hive_broker, "__all__", dir(hive_broker))
        assert "_run_services_argv" not in public_names
        assert "_run_update_argv" not in public_names
        assert "_run_recovery_argv" not in public_names
        assert "_dispatch_service" not in public_names

    def test_ast_no_exec_eval_in_adapters(self):
        import hive_broker.adapters as adapters_module
        src = inspect.getsource(adapters_module)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("exec", "eval", "compile"), (
                    f"Forbidden function {node.func.id} found in adapters"
                )

    def test_dispatch_does_not_call_policy_engine(self):
        src = inspect.getsource(dispatch)
        assert "validate_actions_for_policy" not in src
        assert "policy_engine" not in src
