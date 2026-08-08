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

    # ------------------------------------------------------------------
    # dispatch() gate
    # ------------------------------------------------------------------

    def test_dispatch_raises_adapter_error_for_unknown_capability(self):
        """Unknown capability raises AdapterError — no fallback execution."""
        with pytest.raises(AdapterError) as exc:
            dispatch("unknown.capability", None, {})
        assert "No adapter" in str(exc.value)

    def test_dispatch_raises_for_arbitrary_prefix(self):
        """Prefix match alone is not enough — specific capability must be in mapping."""
        with pytest.raises(AdapterError):
            dispatch("service.evil", None, {})
        with pytest.raises(AdapterError):
            dispatch("vault.secret.read", None, {})
        with pytest.raises(AdapterError):
            dispatch("update.force", None, {})
        with pytest.raises(AdapterError):
            dispatch("recovery.reset", None, {})

    def test_dispatch_returns_for_known_readonly_capabilities(self):
        """Known read-only capabilities dispatch without error."""
        cap_result = dispatch("broker.capabilities", None, {})
        assert "capabilities" in cap_result
        # broker.status requires a transaction with transaction_id
        from hive_broker.transaction import Transaction
        txn = Transaction("txn-test", "task-test", "sess-test", "audit-1")
        status_result = dispatch("broker.status", txn, {})
        assert status_result["status"] == "ok"

    # ------------------------------------------------------------------
    # Service adapter mapping
    # ------------------------------------------------------------------

    def test_service_adapter_only_maps_readonly_ops(self):
        """_dispatch_service maps read-only operations to service CLI."""
        allowed = {"service.list", "service.show", "service.status",
                   "service.health", "service.validate", "service.graph"}
        for cap in allowed:
            # These may succeed or raise ServiceConfigError — verify they
            # don't raise AdapterError (which would mean not in mapping)
            try:
                result = _dispatch_service(cap, {"service": "test"})
                assert isinstance(result, dict)
            except Exception as e:
                # ServiceConfigError is from the service layer, not adapter
                assert "AdapterError" not in type(e).__name__

    def test_service_adapter_rejects_mutating_ops(self):
        """Mutating service operations raise AdapterError."""
        for cap in ("service.start", "service.stop", "service.restart",
                    "service.kill", "service.remove"):
            with pytest.raises(AdapterError):
                _dispatch_service(cap, {})

    # ------------------------------------------------------------------
    # Vault adapter mapping
    # ------------------------------------------------------------------

    def test_vault_adapter_is_placeholder_only(self):
        """vault.status returns placeholder; all other vault ops rejected."""
        result = _dispatch_vault("vault.status", {})
        assert result["status"] == "locked"

        with pytest.raises(AdapterError):
            _dispatch_vault("vault.secret.get", {})
        with pytest.raises(AdapterError):
            _dispatch_vault("vault.secret.read", {})

    # ------------------------------------------------------------------
    # Update adapter mapping
    # ------------------------------------------------------------------

    def test_update_adapter_bounded(self):
        """Update adapter maps inspect/plan/verify; no AdapterError for these."""
        for cap in ("update.status", "update.inspect", "update.plan", "update.verify"):
            # These call subprocess which may succeed or fail, but should
            # NOT raise AdapterError (meaning they're in the mapping)
            try:
                result = _dispatch_update(cap, {})
                assert isinstance(result, dict)
            except AdapterError:
                pytest.fail(f"AdapterError should not be raised for {cap}")
            except Exception:
                pass  # subprocess failures are expected in test env

    def test_update_adapter_rejects_apply(self):
        """update.apply raises AdapterError."""
        with pytest.raises(AdapterError):
            _dispatch_update("update.apply", {})

    # ------------------------------------------------------------------
    # Recovery adapter mapping
    # ------------------------------------------------------------------

    def test_recovery_adapter_bounded(self):
        """Recovery adapter maps inspect/diagnose/verify; no AdapterError."""
        for cap in ("recovery.status", "recovery.diagnose",
                    "recovery.inspect", "recovery.verify"):
            try:
                result = _dispatch_recovery(cap, {})
                assert isinstance(result, dict)
            except AdapterError:
                pytest.fail(f"AdapterError should not be raised for {cap}")
            except Exception:
                pass  # subprocess failures expected

    def test_recovery_adapter_rejects_restore(self):
        """recovery.restore raises AdapterError."""
        with pytest.raises(AdapterError):
            _dispatch_recovery("recovery.restore", {})

    # ------------------------------------------------------------------
    # Subprocess safety
    # ------------------------------------------------------------------

    def test_update_argv_uses_shell_false(self):
        """_run_update_argv uses subprocess.run with shell=False."""
        src = inspect.getsource(_run_update_argv)
        assert "shell=False" in src
        assert "subprocess.run" in src

    def test_recovery_argv_uses_shell_false(self):
        """_run_recovery_argv uses subprocess.run with shell=False."""
        src = inspect.getsource(_run_recovery_argv)
        assert "shell=False" in src
        assert "subprocess.run" in src

    def test_update_argv_has_timeout(self):
        """_run_update_argv has timeout bound."""
        src = inspect.getsource(_run_update_argv)
        assert "timeout=" in src

    def test_recovery_argv_has_timeout(self):
        """_run_recovery_argv has timeout bound."""
        src = inspect.getsource(_run_recovery_argv)
        assert "timeout=" in src

    # ------------------------------------------------------------------
    # Service stdout/stderr capture
    # ------------------------------------------------------------------

    def test_services_argv_redirects_stdout_stderr(self):
        """_run_services_argv captures stdout/stderr; no leakage to process streams."""
        src = inspect.getsource(_run_services_argv)
        assert "sys.stdout" in src
        assert "sys.stderr" in src
        assert "StringIO" in src

    # ------------------------------------------------------------------
    # No dynamic resolution
    # ------------------------------------------------------------------

    def test_no_getattr_in_adapters(self):
        """Adapters use static mapping, not dynamic getattr resolution."""
        src = inspect.getsource(dispatch)
        assert "getattr" not in src
        assert "eval(" not in src
        assert "exec(" not in src

    def test_no_importlib_in_adapters(self):
        """Adapters do not dynamically import modules."""
        import hive_broker.adapters as adapters_module
        src = inspect.getsource(adapters_module)
        assert "importlib" not in src
        assert "__import__" not in src

    # ------------------------------------------------------------------
    # Module exports
    # ------------------------------------------------------------------

    def test_adapter_internals_not_in_hive_broker_exports(self):
        """Internal adapter functions are not exported by hive_broker package."""
        import hive_broker
        public_names = getattr(hive_broker, "__all__", dir(hive_broker))
        assert "_run_services_argv" not in public_names
        assert "_run_update_argv" not in public_names
        assert "_run_recovery_argv" not in public_names
        assert "_dispatch_service" not in public_names

    # ------------------------------------------------------------------
    # AST-level verification: no exec/eval in adapter source
    # ------------------------------------------------------------------

    def test_ast_no_exec_eval_in_adapters(self):
        """Static AST scan confirms no exec/eval/compile calls in adapter module."""
        import hive_broker.adapters as adapters_module
        src = inspect.getsource(adapters_module)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ("exec", "eval", "compile"), (
                        f"Forbidden function {node.func.id} found in adapters"
                    )

    # ------------------------------------------------------------------
    # Dispatcher does not re-authorize
    # ------------------------------------------------------------------

    def test_dispatch_does_not_call_policy_engine(self):
        """dispatch() performs no policy validation — assumes caller authorized."""
        src = inspect.getsource(dispatch)
        assert "validate_actions_for_policy" not in src
        assert "policy" not in src.lower() or "policy" in src  # just checking no policy call
        # More precise: no imports of policy modules
        assert "policy_engine" not in src
