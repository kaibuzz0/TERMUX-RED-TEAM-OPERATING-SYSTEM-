"""Tests for installer/plan.py."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent


class PlanGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_deterministic_plan_generation(self):
        from installer.plan import generate_plan
        plan1 = generate_plan(transaction_id="txn-1")
        plan2 = generate_plan(transaction_id="txn-1")
        d1 = json.dumps({"ops": [(o.op_id, o.op_type) for o in plan1.operations]})
        d2 = json.dumps({"ops": [(o.op_id, o.op_type) for o in plan2.operations]})
        self.assertEqual(d1, d2)

    def test_source_commit_captured(self):
        from installer.plan import generate_plan
        plan = generate_plan(transaction_id="txn-2")
        self.assertNotEqual(plan.source.commit, "")
        # When git is unavailable the commit field may contain an error string.
        self.assertTrue(len(plan.source.commit) == 40 or plan.source.commit.startswith("unknown:"))

    def test_canonical_source_captured(self):
        from installer.plan import generate_plan
        plan = generate_plan(transaction_id="txn-3")
        self.assertTrue(plan.source.canonical_source.name.endswith("Hive Ops Final") or "Hive Ops Final" in str(plan.source.canonical_source))

    def test_operation_order_stable(self):
        from installer.plan import generate_plan
        plan = generate_plan(transaction_id="txn-4")
        ids = [o.op_id for o in plan.operations]
        expected_prefix = ["mkdir-state", "mkdir-config", "mkdir-data", "mkdir-cache", "mkdir-logs", "copy-runtime", "write-manifest"]
        self.assertEqual(ids, expected_prefix)

    def test_rollback_actions_included(self):
        from installer.plan import generate_plan
        plan = generate_plan(transaction_id="txn-5")
        self.assertTrue(len(plan.rollback_operations) > 0)
        self.assertTrue(all("rollback" in o.op_id for o in plan.rollback_operations))

    def test_no_secrets_in_plan(self):
        from installer.plan import generate_plan
        from installer.schema import plan_to_dict
        plan = generate_plan(transaction_id="txn-6")
        text = json.dumps(plan_to_dict(plan))
        for bad in ["password", "token", "secret", "api_key", "credential"]:
            self.assertNotIn(bad, text.lower())

    def test_exact_target_roots_included(self):
        from installer.plan import generate_plan
        from installer.schema import plan_to_dict
        plan = generate_plan(transaction_id="txn-7")
        d = plan_to_dict(plan)
        for key in ("root", "config_root", "state_root", "data_root", "cache_root", "log_root", "staging_root"):
            self.assertIn(key, d["target"])


if __name__ == "__main__":
    unittest.main()
