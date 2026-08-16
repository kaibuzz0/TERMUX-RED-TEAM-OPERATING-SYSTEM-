"""C5-OC: Operations Center cannot invoke mutation adapter.

The Operations Center interacts with the broker only through the public Broker.run()
API with read-only manifests. It never imports adapter internals, and its source
templates must remain bound to broker capabilities marked non-mutating.
"""

from __future__ import annotations

import ast
from pathlib import Path

from operations_center.data_sources import SOURCE_TEMPLATES, make_manifest, broker_run
from hive_broker.capabilities import _CAPABILITY_NAMES, BROKER_CAPABILITIES


class TestOperationsCenterCannotInvokeMutation:
    def test_source_templates_are_readonly(self):
        for name, request in SOURCE_TEMPLATES.items():
            assert request.manifest.get("read_only") is True, f"Template {name} is not read_only"

    def test_source_templates_single_action(self):
        for name, request in SOURCE_TEMPLATES.items():
            actions = request.manifest.get("allowed_actions", [])
            assert len(actions) == 1, f"Template {name} has {len(actions)} actions"

    def test_source_templates_no_mutating_actions(self):
        mutation_by_name = {cap.name: cap.mutation for cap in BROKER_CAPABILITIES}
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action in mutation_by_name, f"Template {name} capability {action} not advertised"
            assert mutation_by_name[action] is False, f"Template {name} has mutating action: {action}"

    def test_source_templates_match_advertised_capabilities(self):
        advertised = set(_CAPABILITY_NAMES)
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action in advertised, f"Template {name} capability {action} not advertised"

    def test_make_manifest_produces_readonly(self):
        manifest = make_manifest("test-intent", "service.status", "test-id")
        assert manifest["read_only"] is True
        assert manifest["allowed_actions"] == ["service.status"]
        assert manifest["required_capabilities"] == ["service.status"]

    def test_no_hive_broker_adapters_imported(self):
        oc_dir = Path(__file__).parent.parent / "operations_center"
        for py_file in oc_dir.glob("*.py"):
            src = py_file.read_text()
            assert "from hive_broker.adapters" not in src, f"{py_file.name} imports adapters"
            assert "import hive_broker.adapters" not in src, f"{py_file.name} imports adapters module"

    def test_no_adapter_internals_referenced(self):
        oc_dir = Path(__file__).parent.parent / "operations_center"
        forbidden = {
            "_run_services_argv", "_run_update_argv", "_run_recovery_argv",
            "_dispatch_service", "_dispatch_vault", "_dispatch_update",
            "_dispatch_recovery", "dispatch(",
        }
        for py_file in oc_dir.glob("*.py"):
            src = py_file.read_text()
            for term in forbidden:
                assert term not in src, f"Forbidden term {term!r} in {py_file.name}"

    def test_ast_no_exec_eval_in_operations_center(self):
        oc_dir = Path(__file__).parent.parent / "operations_center"
        for py_file in oc_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in ("exec", "eval", "compile"), (
                        f"Forbidden function {node.func.id} in {py_file.name}"
                    )

    def test_broker_run_calls_broker_run(self):
        import inspect
        src = inspect.getsource(broker_run)
        assert "Broker(" in src
        assert "broker.run(" in src
        assert "dispatch(" not in src
        assert "_dispatch" not in src

    def test_oc_cli_no_mutation_commands(self):
        import inspect
        import operations_center.cli as cli_module
        src = inspect.getsource(cli_module)
        mutating_cmds = {"start", "stop", "restart", "kill", "remove",
                         "apply", "force", "restore", "reset", "commit", "write"}
        for cmd in mutating_cmds:
            assert f'add_parser("{cmd}"' not in src
            assert f"add_parser('{cmd}'" not in src

    def test_data_sources_only_use_readonly_capabilities(self):
        readonly_caps = {cap.name for cap in BROKER_CAPABILITIES if not cap.mutation}
        for name, request in SOURCE_TEMPLATES.items():
            action = request.manifest["allowed_actions"][0]
            assert action in readonly_caps, f"Template {name} uses mutating/unadvertised capability: {action}"
