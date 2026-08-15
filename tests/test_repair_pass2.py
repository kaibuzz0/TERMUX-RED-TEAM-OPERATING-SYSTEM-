"""Targeted regression tests for Hive OS Native Termux Repair Pass 2.

Covers:
- broker intent registration for broker-capabilities, broker-status, policy-status
- OC data_sources intent fix (inspect-service-health -> inspect-service-status)
- broker adapter graceful skip when service=None
- OC broker capability extraction from nested result
- truthful physical validation in overview
- no mutation capabilities reachable through OC
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "bin" / "hive"


class RepairPass2Tests(unittest.TestCase):
    """Regression tests for Operations Center / Broker contract."""

    def _run_launcher(self, *args, cwd=None, env=None):
        env = env or os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, str(LAUNCHER)] + list(args)
        return subprocess.run(cmd, cwd=cwd or str(REPO_ROOT), capture_output=True, text=True, env=env)

    # ── Intent registration ──
    def test_broker_capabilities_intent_exists(self):
        from hive_broker.intents import get_intent
        intent = get_intent("broker-capabilities")
        self.assertIn("broker.capabilities", intent.allowed_actions)

    def test_broker_status_intent_exists(self):
        from hive_broker.intents import get_intent
        intent = get_intent("broker-status")
        self.assertIn("broker.status", intent.allowed_actions)

    def test_policy_status_intent_exists(self):
        from hive_broker.intents import get_intent
        intent = get_intent("policy-status")
        self.assertIn("policy.status", intent.allowed_actions)

    # ── OC data_sources intent fix ──
    def test_service_health_intent_is_inspect_service_status(self):
        from operations_center.data_sources import SOURCE_TEMPLATES
        req = SOURCE_TEMPLATES["service_health"]
        self.assertEqual(req.manifest["intent"], "inspect-service-status",
                         "service_health must use inspect-service-status intent")

    # ── Broker adapter skip when no service ──
    def test_service_status_skips_when_no_service(self):
        from hive_broker.adapters import _dispatch_service
        result = _dispatch_service("service.status", {"service": None})
        self.assertEqual(result["status"], "skipped")

    def test_service_health_skips_when_no_service(self):
        from hive_broker.adapters import _dispatch_service
        result = _dispatch_service("service.health", {"service": ""})
        self.assertEqual(result["status"], "skipped")

    # ── OC broker capability extraction ──
    def test_deep_capabilities_reads_nested_payload(self):
        from operations_center.collectors import _deep_capabilities
        # Actual broker adapter returns: result = {"capabilities": {"schema_version": 1, "capabilities": [...]}}
        source = {
            "status": "AVAILABLE",
            "result": {
                "status": "success",
                "results": [{
                    "action": "broker.capabilities",
                    "result": {
                        "capabilities": {
                            "schema_version": 1,
                            "capabilities": [
                                {"name": "broker.capabilities", "mutation": False},
                                {"name": "service.list", "mutation": False},
                            ],
                        },
                    },
                }],
            },
        }
        caps = _deep_capabilities(source)
        self.assertEqual(len(caps), 2)
        self.assertEqual(caps[0]["name"], "broker.capabilities")

    # ── Physical validation truthfulness ──
    def test_detect_physical_validation_on_aarch64_linux(self):
        from unittest.mock import patch
        from operations_center.collectors import _detect_physical_validation
        with patch("platform.system", return_value="Linux"), \
             patch("platform.machine", return_value="aarch64"):
            result = _detect_physical_validation()
            self.assertIn("VALIDATED", result)
            self.assertIn("REPAIR VALIDATION IN PROGRESS", result)

    # ── No mutation through OC read-only views ──
    def test_views_are_read_only(self):
        from operations_center.cli import _VIEWS
        for name in _VIEWS:
            self.assertNotIn(name, ("start", "stop", "restart", "apply", "restore"),
                             f"view {name} must not be a mutation command")

    # ── Real device: ops overview from home ──
    def test_ops_overview_from_home(self):
        result = self._run_launcher("ops", "--json", "overview", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"ops overview from home must succeed: {result.stderr}")
        # Should not contain legacy-only output
        self.assertNotIn("Hive Ops Final", result.stdout)
        data = json.loads(result.stdout)
        self.assertIn("data", data)
        self.assertIn("physical_validation", data["data"])
        pv = data["data"]["physical_validation"]
        self.assertIn("VALIDATED", pv)

    # ── Real device: ops broker view from home ──
    def test_ops_broker_from_home(self):
        result = self._run_launcher("ops", "--json", "broker", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"ops broker from home must succeed: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("data", data)
        self.assertIn("capabilities", data["data"])

    # ── Real device: ops services view from home ──
    def test_ops_services_from_home(self):
        result = self._run_launcher("ops", "--json", "services", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"ops services from home must succeed: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("services", data)
        self.assertIsInstance(data["services"], list)

    # ── Runpy warning absent ──
    def test_no_runpy_warning_on_ops(self):
        result = self._run_launcher("ops", cwd=str(Path.home()))
        self.assertNotIn("RuntimeWarning", result.stderr)


if __name__ == "__main__":
    unittest.main()
