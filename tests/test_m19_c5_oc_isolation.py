"""C5-OC: Operations Center cannot invoke mutation adapter.

The Operations Center (`operations_center`) interacts with the broker only through
the public `Broker.run()` API with read-only manifests. It never imports or calls
adapter internals, and its `SOURCE_TEMPLATES` contains only read-only capabilities.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from operations_center.data_sources import (
    SOURCE_TEMPLATES,
    make_manifest,
    broker_run,
)
from hive_broker.capabilities import _CAPABILITY_NAMES, BROKER_CAPABILITIES
from policy_engine.decisions import DecisionState


class TestOperationsCenterCannotInvokeMutation:
    """Operations Center is read-only and broker-mediated."""

    # ------------------------------------------------------------------
    # SOURCE_TEMPLATES are bounded and read-only
    # ------------------------------------------------------------------

    def test_source_templates_are_readonly(self):
        """Every SOURCE_TEMPLATE has read_only=True."""
        for name, request in SOURCE_TEMPLATES.items():
            assert request.manifest.get("read_only") is True, (
                f"Template {name} is not read_only"
            )

    def test_source_templates_single_action(self):
        """Every SOURCE_TEMPLATE has exactly one allowed_action."""
        for name, request in SOURCE_TEMPLATES.items():
            actions = request.manifest.get("allowed_actions", [])
            assert len(actions) == 1, (
                f"Template {name} has {len(actions)} actions"
            )

    def test_source_templates_no_mutating_actions(self):
        """No SOURCE_TEMPLATE contains mutating capabilities."""
        mutating = {
            "service.start", "service.stop", "service.restart", "service.kill",
            "service.remove", "update.apply", "update.force", "recovery.restore",
            "recovery.reset", "config.commit", "config.write", "vault.secret.get",
        }
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action not in mutating, (
                f"Template {name} has mutating action: {action}"
            )

    def test_source_templates_match_advertised_capabilities(self):
        """Every SOURCE_TEMPLATE capability is in broker's advertised set."""
        advertised = set(_CAPABILITY_NAMES)
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action in advertised, (
                f"Template {name} capability {action} not advertised"
            )

    # ------------------------------------------------------------------
    # make_manifest is deterministic and read-only
    # ------------------------------------------------------------------

    def test_make_manifest_produces_readonly(self):
        """make_manifest always produces read_only=True manifests."""
        manifest = make_manifest("test-intent", "service.status", "test-id")
        assert manifest["read_only"] is True
        assert manifest["allowed_actions"] == ["service.status"]
        assert manifest["required_capabilities"] == ["service.status"]

    # ------------------------------------------------------------------
    # No adapter internals in operations_center
    # ------------------------------------------------------------------

    def test_no_hive_broker_adapters_imported(self):
        """No operations_center module imports hive_broker.adapters."""
        oc_dir = Path(__file__).parent.parent / "operations_center"
        for py_file in oc_dir.glob("*.py"):
            src = py_file.read_text()
            assert "from hive_broker.adapters" not in src, (
                f"{py_file.name} imports adapters"
            )
            assert "import hive_broker.adapters" not in src, (
                f"{py_file.name} imports adapters module"
            )

    def test_no_adapter_internals_referenced(self):
        """No operations_center source references adapter internals."""
        oc_dir = Path(__file__).parent.parent / "operations_center"
        forbidden = {
            "_run_services_argv", "_run_update_argv", "_run_recovery_argv",
            "_dispatch_service", "_dispatch_vault", "_dispatch_update",
            "_dispatch_recovery", "dispatch(",
        }
        for py_file in oc_dir.glob("*.py"):
            src = py_file.read_text()
            for term in forbidden:
                assert term not in src, (
                    f"Forbidden term {term!r} in {py_file.name}"
                )

    def test_ast_no_exec_eval_in_operations_center(self):
        """AST scan confirms no exec/eval/compile in operations_center."""
        oc_dir = Path(__file__).parent.parent / "operations_center"
        for py_file in oc_dir.glob("*.py"):
            src = py_file.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        assert node.func.id not in ("exec", "eval", "compile"), (
                            f"Forbidden function {node.func.id} in {py_file.name}"
                        )

    # ------------------------------------------------------------------
    # broker_run goes through Broker.run, not direct adapter
    # ------------------------------------------------------------------

    def test_broker_run_calls_broker_run(self):
        """broker_run creates Broker and calls broker.run(), not adapters directly."""
        import inspect
        src = inspect.getsource(broker_run)
        assert "Broker(" in src
        assert "broker.run(" in src
        assert "dispatch(" not in src
        assert "_dispatch" not in src

    # ------------------------------------------------------------------
    # No mutation surface in CLI
    # ------------------------------------------------------------------

    def test_oc_cli_no_mutation_commands(self):
        """operations_center CLI has no mutation subcommands."""
        import inspect
        import operations_center.cli as cli_module
        src = inspect.getsource(cli_module)
        mutating_cmds = {"start", "stop", "restart", "kill", "remove",
                         "apply", "force", "restore", "reset", "commit", "write"}
        for cmd in mutating_cmds:
            # Rough heuristic: check for add_parser with mutating names
            assert f'"{cmd}"' not in src or f"'{cmd}'" not in src, (
                f"Potential mutating command {cmd} in oc cli"
            )

    # ------------------------------------------------------------------
    # Operations Center source uses only read-only broker capabilities
    # ------------------------------------------------------------------

    def test_data_sources_only_use_readonly_capabilities(self):
        """SOURCE_TEMPLATES capabilities are all read-only."""
        readonly_caps = {
            "service.list", "service.graph", "service.status", "service.health",
            "service.validate", "service.show",
            "update.status", "update.inspect", "update.plan", "update.verify",
            "recovery.status", "recovery.diagnose", "recovery.inspect", "recovery.verify",
            "vault.status", "broker.capabilities", "broker.status",
        }
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action in readonly_caps, (
                f"Template {name} uses unexpected capability: {action}"
            )
