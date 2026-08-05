"""Tests for Hive broker."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _tmp_dirs():
    tmp = Path(tempfile.mkdtemp())
    return tmp / "state", tmp / "logs", tmp


class ManifestSchemaTests(unittest.TestCase):
    def test_valid_manifest(self):
        from hive_broker.schema import validate_manifest
        m = {
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "inspect-service-status",
            "required_capabilities": ["service.status"],
            "allowed_actions": ["service.status"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
            "audit_level": "normal",
        }
        self.assertEqual(validate_manifest(m)["task_id"], "t1")

    def test_unknown_schema(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 99})

    def test_unknown_field(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c"], "allowed_actions": ["c"], "read_only": True, "timeout_seconds": 30, "extra": 1})

    def test_duplicate_action(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c"], "allowed_actions": ["c", "c"], "read_only": True, "timeout_seconds": 30})

    def test_duplicate_capability(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c", "c"], "allowed_actions": ["c"], "read_only": True, "timeout_seconds": 30})

    def test_timeout_bounds(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c"], "allowed_actions": ["c"], "read_only": True, "timeout_seconds": 0})
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c"], "allowed_actions": ["c"], "read_only": True, "timeout_seconds": 10000})

    def test_read_only_mismatch(self):
        from hive_broker.schema import validate_manifest, ManifestError
        with self.assertRaises(ManifestError):
            validate_manifest({"schema_version": 1, "task_id": "t", "requestor": "h", "intent": "i", "required_capabilities": ["c"], "allowed_actions": ["c"], "read_only": "yes", "timeout_seconds": 30})


class CapabilityTests(unittest.TestCase):
    def test_capability_endpoint(self):
        from hive_broker.capabilities import get_capabilities
        caps = get_capabilities()
        self.assertEqual(caps["schema_version"], 1)
        names = [c["name"] for c in caps["capabilities"]]
        self.assertIn("service.status", names)
        self.assertNotIn("service.start", names)
        self.assertNotIn("vault.get", names)

    def test_required_subset(self):
        from hive_broker.capabilities import validate_required
        validate_required(["service.status"])

    def test_unsupported_required(self):
        from hive_broker.capabilities import validate_required, CapabilityError
        with self.assertRaises(CapabilityError):
            validate_required(["service.start"])


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        from hive_broker.policy import get_policy
        self.policy = get_policy("observer")

    def test_valid_read_only(self):
        from hive_broker.validator import validate_task_manifest
        m = {
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "inspect-service-status",
            "required_capabilities": ["service.status", "service.health"],
            "allowed_actions": ["service.status"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
            "audit_level": "normal",
        }
        result = validate_task_manifest(m, self.policy)
        self.assertEqual(result["intent"], "inspect-service-status")

    def test_action_not_in_required_capabilities(self):
        from hive_broker.validator import validate_task_manifest
        from hive_broker.errors import ManifestError
        m = {
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "inspect-service-status",
            "required_capabilities": ["service.status"],
            "allowed_actions": ["service.health"],
            "read_only": True,
            "timeout_seconds": 30,
        }
        with self.assertRaises(ManifestError):
            validate_task_manifest(m, self.policy)


class TransactionTests(unittest.TestCase):
    def test_unique_transaction(self):
        from hive_broker.transaction import generate_transaction
        t1 = generate_transaction("task-1", "sess-1", "audit-1")
        t2 = generate_transaction("task-1", "sess-1", "audit-2")
        self.assertNotEqual(t1.transaction_id, t2.transaction_id)
        self.assertEqual(t1.task_id, "task-1")


class BrokerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.state, self.logs, self.tmp = _tmp_dirs()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_capabilities_command(self):
        from hive_broker import Broker
        broker = Broker(self.state, self.logs)
        caps = broker.capabilities()
        self.assertIn("broker.capabilities", [c["name"] for c in caps["capabilities"]])

    def test_validate_valid_manifest(self):
        from hive_broker import Broker
        broker = Broker(self.state, self.logs)
        result = broker.validate({
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "inspect-service-status",
            "required_capabilities": ["service.status"],
            "allowed_actions": ["service.status"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
            "audit_level": "normal",
        })
        self.assertTrue(result["valid"])

    def test_run_read_only(self):
        from hive_broker import Broker
        broker = Broker(self.state, self.logs)
        result = broker.run({
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "list-services",
            "required_capabilities": ["service.list"],
            "allowed_actions": ["service.list"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
            "audit_level": "normal",
        })
        self.assertIn("transaction_id", result)
        self.assertEqual(result["task_id"], "t1")

    def test_stop_session(self):
        from hive_broker import Broker
        broker = Broker(self.state, self.logs)
        st = broker.stop()
        self.assertTrue(st["stopped"])

    def test_audit_lookup(self):
        from hive_broker import Broker
        broker = Broker(self.state, self.logs)
        result = broker.run({
            "schema_version": 1,
            "task_id": "t1",
            "requestor": "hermes",
            "intent": "list-services",
            "required_capabilities": ["service.list"],
            "allowed_actions": ["service.list"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 30,
            "audit_level": "normal",
        })
        records = broker.audit.read_transaction(result["transaction_id"])
        self.assertTrue(len(records) >= 1)


class VersionCompatibilityTests(unittest.TestCase):
    def test_packaged_runtime_without_git(self):
        import os
        old = os.environ.get("HIVE_SOURCE_COMMIT")
        try:
            os.environ["HIVE_SOURCE_COMMIT"] = "packaged123"
            from hive_broker.version import get_runtime_metadata
            meta = get_runtime_metadata()
            self.assertEqual(meta["source_commit"], "packaged123")
        finally:
            if old is None:
                os.environ.pop("HIVE_SOURCE_COMMIT", None)
            else:
                os.environ["HIVE_SOURCE_COMMIT"] = old

    def test_lexical_hash_not_used(self):
        from hive_broker.version import check_allowed_since_commit
        # Should not raise based on lexical comparison; only on ancestry when git available.
        check_allowed_since_commit({"allowed_since_commit": "0000000000000000000000000000000000000000"})


if __name__ == "__main__":
    unittest.main()
