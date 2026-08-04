"""Tests for lib/hive_service_loader.py.

These tests validate that services.json is parsed, paths are resolved safely,
commands become argument arrays, and no service is started during validation.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent


class LoaderDiscoveryTests(unittest.TestCase):
    def test_loader_module_exists(self):
        loader = REPO_ROOT / "lib" / "hive_service_loader.py"
        self.assertTrue(loader.is_file(), "service loader module must exist")

    def test_services_file_exists(self):
        svc = REPO_ROOT / "Hive Ops Final" / "etc" / "services.json"
        self.assertTrue(svc.is_file())


class SchemaTests(unittest.TestCase):
    def test_services_json_valid_schema(self):
        import json
        with open(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("schema", data)
        self.assertIn("services", data)

    def test_services_json_no_root_paths(self):
        text = (REPO_ROOT / "Hive Ops Final" / "etc" / "services.json").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("/root/hive", text, "services.json must not hardcode /root/hive")
        self.assertNotIn("/root/Hive Ops Final", text)

    def test_service_list_unchanged(self):
        import json
        with open(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(set(data["services"].keys()), {"hive-daemon", "swarm-registry", "watchdog"})

    def test_auto_start_states_unchanged(self):
        import json
        with open(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data["services"]["hive-daemon"]["auto_start"])
        self.assertFalse(data["services"]["swarm-registry"]["auto_start"])
        self.assertTrue(data["services"]["watchdog"]["auto_start"])


class ValidationNonMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HIVE_HOME"] = str(self.tmp / "hive")
        os.environ["HIVE_CONFIG_ROOT"] = str(self.tmp / "config")
        os.environ["HIVE_STATE_ROOT"] = str(self.tmp / "state")
        os.environ["HIVE_DATA_ROOT"] = str(self.tmp / "data")
        os.environ["HIVE_CACHE_ROOT"] = str(self.tmp / "cache")
        os.environ["HIVE_LOG_ROOT"] = str(self.tmp / "logs")
        os.environ["HIVE_TEMP_ROOT"] = str(self.tmp / "tmp")
        os.environ["HIVE_OS_ROOT"] = str(self.tmp / "hive-os")
        os.environ["HIVE_SWARM_ROOT"] = str(self.tmp / "hive-swarm")
        os.environ["HIVE_FINAL"] = str(REPO_ROOT / "Hive Ops Final")
        os.environ["HIVE_ETC"] = str(REPO_ROOT / "Hive Ops Final" / "etc")
        os.environ["HOME"] = str(self.tmp)
        os.environ["TMPDIR"] = str(self.tmp / "tmp")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validate_services_file_no_errors(self):
        from lib.hive_service_loader import validate_services_file
        report = validate_services_file(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", validate_executables=False)
        self.assertEqual(report["errors"], [], f"Unexpected errors: {report['errors']}")

    def test_validate_creates_no_directories(self):
        from lib.hive_service_loader import validate_services_file
        validate_services_file(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", validate_executables=False)
        for sub in ["hive", "config", "state", "data", "logs"]:
            self.assertFalse((self.tmp / sub).exists(), f"Validation created {sub}")


class CommandSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HIVE_HOME"] = str(self.tmp / "hive")
        os.environ["HIVE_CONFIG_ROOT"] = str(self.tmp / "config")
        os.environ["HIVE_STATE_ROOT"] = str(self.tmp / "state")
        os.environ["HIVE_DATA_ROOT"] = str(self.tmp / "data")
        os.environ["HIVE_CACHE_ROOT"] = str(self.tmp / "cache")
        os.environ["HIVE_LOG_ROOT"] = str(self.tmp / "logs")
        os.environ["HIVE_TEMP_ROOT"] = str(self.tmp / "tmp")
        os.environ["HIVE_OS_ROOT"] = str(self.tmp / "hive-os")
        os.environ["HIVE_SWARM_ROOT"] = str(self.tmp / "hive-swarm")
        os.environ["HIVE_FINAL"] = str(REPO_ROOT / "Hive Ops Final")
        os.environ["HIVE_ETC"] = str(REPO_ROOT / "Hive Ops Final" / "etc")
        os.environ["HOME"] = str(self.tmp)
        os.environ["TMPDIR"] = str(self.tmp / "tmp")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_commands_are_argument_arrays(self):
        from lib.hive_service_loader import validate_services_file
        report = validate_services_file(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", validate_executables=False)
        for name, svc in report["services"].items():
            for field in ("start", "stop", "status", "restart"):
                if field in svc["resolved"]:
                    self.assertIsInstance(svc["resolved"][field], list, f"{name}.{field} must be a list")

    def test_no_shell_metacharacters_in_commands(self):
        from lib.hive_service_loader import validate_services_file
        report = validate_services_file(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", validate_executables=False)
        for name, svc in report["services"].items():
            self.assertEqual(svc["errors"], [], f"{name} has command errors")

    def test_log_paths_contained_under_log_root(self):
        from lib.hive_service_loader import validate_services_file
        report = validate_services_file(REPO_ROOT / "Hive Ops Final" / "etc" / "services.json", validate_executables=False)
        log_root = Path(self.tmp / "logs").resolve()
        for name, svc in report["services"].items():
            log = Path(svc["resolved"]["log"]).resolve()
            try:
                log.relative_to(log_root)
            except ValueError:
                self.fail(f"{name} log path escapes log-root: {log}")


class CliInvocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(REPO_ROOT)
        self.env["HIVE_HOME"] = str(self.tmp / "hive")
        self.env["HIVE_CONFIG_ROOT"] = str(self.tmp / "config")
        self.env["HIVE_STATE_ROOT"] = str(self.tmp / "state")
        self.env["HIVE_DATA_ROOT"] = str(self.tmp / "data")
        self.env["HIVE_CACHE_ROOT"] = str(self.tmp / "cache")
        self.env["HIVE_LOG_ROOT"] = str(self.tmp / "logs")
        self.env["HIVE_TEMP_ROOT"] = str(self.tmp / "tmp")
        self.env["HIVE_OS_ROOT"] = str(self.tmp / "hive-os")
        self.env["HIVE_SWARM_ROOT"] = str(self.tmp / "hive-swarm")
        self.env["HIVE_FINAL"] = str(REPO_ROOT / "Hive Ops Final")
        self.env["HIVE_ETC"] = str(REPO_ROOT / "Hive Ops Final" / "etc")
        self.env["HOME"] = str(self.tmp)
        self.env["TMPDIR"] = str(self.tmp / "tmp")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_validate_services_json(self):
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bin" / "hive"), "--validate-services-json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=self.env,
            timeout=60,
        )
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        data = json.loads(r.stdout)
        self.assertEqual(data["schema"], 2)
        self.assertEqual(set(data["services"].keys()), {"hive-daemon", "swarm-registry", "watchdog"})


if __name__ == "__main__":
    unittest.main()
