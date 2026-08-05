"""Tests for Operations Center."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _tmp_dirs():
    tmp = Path(tempfile.mkdtemp())
    return tmp / "state", tmp / "logs", tmp


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_no_direct_service_mutation_imports(self):
        import operations_center.collectors as collectors
        text = Path(collectors.__file__).read_text(encoding="utf-8")
        self.assertNotIn("services.cli", text)
        self.assertNotIn("service.start", text)
        self.assertNotIn("service.stop", text)

    def test_broker_is_only_data_source(self):
        import operations_center.data_sources as ds
        text = Path(ds.__file__).read_text(encoding="utf-8")
        self.assertIn("hive_broker", text)

    def test_no_arbitrary_capability_selection(self):
        import operations_center.cli as cli
        text = Path(cli.__file__).read_text(encoding="utf-8")
        self.assertNotIn("allowed_actions", text)
        self.assertNotIn("required_capabilities", text)


class SchemaTests(unittest.TestCase):
    def test_severity_values(self):
        from operations_center.schema import Severity
        self.assertEqual(Severity.WARNING.value, "WARNING")

    def test_source_status_values(self):
        from operations_center.schema import SourceStatus
        self.assertIn("AVAILABLE", [s.value for s in SourceStatus])


class RedactionTests(unittest.TestCase):
    def test_secret_value_redacted(self):
        from operations_center.redaction import redact_value
        result = redact_value({"password": "supersecret"})
        self.assertEqual(result["password"], "***REDACTED***")

    def test_control_characters_sanitized(self):
        from operations_center.redaction import redact_value
        result = redact_value({"msg": "hello\x00world"})
        self.assertNotIn("\x00", result["msg"])


class ViewModelTests(unittest.TestCase):
    def test_service_totals(self):
        from operations_center.view_models import service_view_model
        services = [
            {"name": "a", "state": "RUNNING"},
            {"name": "b", "state": "FAILED"},
            {"name": "c", "state": "CRASH_LOOP"},
            {"name": "d", "state": "DISABLED", "classification": "LEGACY_ONLY"},
        ]
        vm = service_view_model(services)
        self.assertEqual(vm["total"], 4)
        self.assertEqual(vm["running"], 1)
        self.assertEqual(vm["failed"], 1)
        self.assertEqual(vm["crash_loop"], 1)
        self.assertEqual(vm["disabled"], 1)
        self.assertEqual(vm["legacy_only"], 1)


class DiagnosticsTests(unittest.TestCase):
    def test_crash_loop_critical(self):
        from operations_center.diagnostics import evaluate
        findings = evaluate("overview", {"services": {"crash_loop": 2, "failed": 0, "legacy_only": 0}}, {})
        codes = [f["code"] for f in findings]
        self.assertIn("OC-SVC-001", codes)

    def test_no_auto_remediation(self):
        from operations_center.diagnostics import evaluate
        findings = evaluate("overview", {}, {})
        for f in findings:
            self.assertFalse(f["auto_remediation"])


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.state, self.logs, self.tmp = _tmp_dirs()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_snapshot_id_generated(self):
        from operations_center.collectors import Collector
        c = Collector(self.state, self.logs)
        self.assertTrue(c.snapshot_id.startswith("snap-"))

    def test_overview_partial(self):
        from operations_center.collectors import Collector
        c = Collector(self.state, self.logs, source_timeout=2.0)
        data = c.collect_overview()
        self.assertIn("status", data)
        self.assertIn("snapshot_id", data)

    def test_services_view(self):
        from operations_center.collectors import Collector
        c = Collector(self.state, self.logs, source_timeout=2.0)
        data = c.collect_services()
        self.assertEqual(data["view"], "services")


class RenderTests(unittest.TestCase):
    def test_render_json_no_ansi(self):
        from operations_center.render import render_json
        import json
        data = {"view": "overview", "data": {"vault_state": "LOCKED"}}
        out = json.loads(render_json(data))
        self.assertEqual(out["view"], "overview")

    def test_render_text_contains_view(self):
        from operations_center.render import render_text
        data = {
            "view": "overview",
            "snapshot_id": "snap-test",
            "status": "success",
            "generated_at": "2026-08-04T12:00:00Z",
            "data": {"hive_version": "fc13e2f", "vault_state": "LOCKED"},
            "sources": {},
            "diagnostics": [],
            "errors": [],
        }
        text = render_text(data)
        self.assertIn("Hive OS Operations Center", text)
        self.assertIn("LOCKED", text)


class CliTests(unittest.TestCase):
    def test_unknown_view_rejected(self):
        from operations_center.cli import main
        import io, sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            code = main(["unknown-view"])
        except SystemExit as exc:
            code = exc.code
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        self.assertNotEqual(code, 0)

    def test_json_output(self):
        from operations_center.cli import main
        import io, sys, json
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = main(["overview", "--json", "--timeout", "2"])
        finally:
            out = sys.stdout.getvalue()
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["view"], "overview")
        self.assertNotIn("secret", str(data))


if __name__ == "__main__":
    unittest.main()
