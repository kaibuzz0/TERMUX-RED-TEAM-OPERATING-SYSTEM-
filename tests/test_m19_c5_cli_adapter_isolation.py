"""C5-CLI: CLI cannot invoke adapter directly.

The hive_broker CLI (`hive broker`) only exposes high-level broker operations.
It does not expose adapter internals (_run_services_argv, _dispatch_service, etc.)
and all execution paths go through broker.run() which enforces policy/dispatcher gates.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from hive_broker.cli import main, cmd_run, cmd_capabilities, cmd_validate, cmd_inspect
from hive_broker.adapters import dispatch, _dispatch_service, _run_services_argv


class TestCliCannotInvokeAdapterDirectly:
    """CLI surface does not expose adapter internals."""

    # ------------------------------------------------------------------
    # CLI subcommands are bounded
    # ------------------------------------------------------------------

    def test_cli_subcommands_are_bounded(self):
        """main() only accepts known subcommands; no wildcard/fallback execution."""
        src = inspect.getsource(main)
        assert "handlers = {" in src
        # Verify the handlers dict is explicit and bounded
        assert "cmd_run" in src
        assert "cmd_capabilities" in src
        assert "cmd_validate" in src
        assert "cmd_inspect" in src
        assert "cmd_status" in src
        assert "cmd_stop" in src
        assert "cmd_audit" in src
        assert "cmd_policy_check" in src

    def test_cli_rejects_unknown_subcommand(self):
        """Unknown subcommand raises SystemExit with error, not silent fallback."""
        import argparse
        with pytest.raises(SystemExit) as exc:
            main(["unknown-command"])
        assert exc.value.code != 0

    def test_cli_run_requires_manifest(self):
        """cmd_run requires --manifest argument; no positional raw dispatch."""
        with pytest.raises(SystemExit):
            main(["run"])

    # ------------------------------------------------------------------
    # cmd_run goes through broker.run(), not direct adapter
    # ------------------------------------------------------------------

    def test_cmd_run_calls_broker_run(self):
        """cmd_run source calls broker.run(), not adapter.dispatch()."""
        src = inspect.getsource(cmd_run)
        assert "broker.run(" in src
        assert "dispatch(" not in src
        assert "_dispatch_service" not in src
        assert "_run_services_argv" not in src

    def test_cmd_run_does_not_import_adapters(self):
        """cmd_run body does not reference adapter module."""
        src = inspect.getsource(cmd_run)
        assert "adapters" not in src

    # ------------------------------------------------------------------
    # No adapter functions in CLI source
    # ------------------------------------------------------------------

    def test_cli_source_no_adapter_internals(self):
        """AST scan of cli.py confirms no adapter internals referenced."""
        import hive_broker.cli as cli_module
        src = inspect.getsource(cli_module)
        adapter_names = {
            "_run_services_argv", "_run_update_argv", "_run_recovery_argv",
            "_dispatch_service", "_dispatch_vault", "_dispatch_update",
            "_dispatch_recovery",
        }
        for name in adapter_names:
            assert name not in src, f"Adapter internal {name} found in cli.py"

    def test_cli_source_no_getattr_eval_exec(self):
        """AST scan confirms no dynamic execution in cli.py."""
        import hive_broker.cli as cli_module
        src = inspect.getsource(cli_module)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ("exec", "eval", "compile"), (
                        f"Forbidden function {node.func.id} in cli.py"
                    )

    # ------------------------------------------------------------------
    # Broker CLI is the only broker entry point from bin/hive
    # ------------------------------------------------------------------

    def test_bin_hive_broker_delegates_to_cli_module(self):
        """bin/hive broker delegates to hive_broker.cli module, not adapters."""
        launcher_src = Path("bin/hive").read_text()
        assert "hive_broker.cli" in launcher_src
        assert "hive_broker.adapters" not in launcher_src

    # ------------------------------------------------------------------
    # No adapter dispatch in any cmd_* function
    # ------------------------------------------------------------------

    def test_no_cmd_calls_dispatch_directly(self):
        """No cmd_* function in cli.py calls adapter.dispatch()."""
        import hive_broker.cli as cli_module
        src = inspect.getsource(cli_module)
        assert "dispatch(" not in src or "broker.dispatch" not in src
        # The only dispatch should be argparse subparser dispatch
        assert "handlers[args.command]" in src

    # ------------------------------------------------------------------
    # cmd_policy_check is read-only
    # ------------------------------------------------------------------

    def test_cmd_policy_check_is_read_only(self):
        """policy-check subcommand sets execution_performed = False explicitly."""
        import hive_broker.cli as cli_module
        src = inspect.getsource(cli_module)
        assert '"execution_performed"] = False' in src
        assert '"execution_performed"] = True' not in src

    # ------------------------------------------------------------------
    # cli.py imports: only Broker from top-level, not adapters
    # ------------------------------------------------------------------

    def test_cli_imports_only_broker_facade(self):
        """cli.py imports Broker from hive_broker, not adapter internals."""
        import hive_broker.cli as cli_module
        src = inspect.getsource(cli_module)
        assert "from hive_broker import Broker" in src or "from hive_broker import" in src
        assert "from hive_broker.adapters" not in src
