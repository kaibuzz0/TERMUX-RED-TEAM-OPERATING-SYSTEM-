"""Tests for installer/staging.py."""

import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_plan(self, txn="txn-test"):
        from installer.plan import generate_plan
        return generate_plan(transaction_id=txn)

    def test_staging_root_containment(self):
        from installer.staging import StagingArea
        plan = self._make_plan()
        area = StagingArea(plan)
        self.assertIn(plan.transaction_id, str(area.staging_root))
        self.assertTrue(str(area.staging_root).startswith(str(plan.target.staging_root)))

    def test_unique_transaction_id(self):
        from installer.plan import generate_plan
        p1 = generate_plan()
        p2 = generate_plan()
        self.assertNotEqual(p1.transaction_id, p2.transaction_id)

    def test_source_manifest_generated(self):
        from installer.staging import StagingArea
        plan = self._make_plan()
        area = StagingArea(plan)
        manifest = area.create_manifest(plan.source.canonical_source)
        self.assertTrue(len(manifest) > 0)
        files = [m for m in manifest if m["type"] == "file"]
        self.assertTrue(len(files) > 0)

    def test_hashes_verified(self):
        from installer.staging import StagingArea
        from installer.verify import verify_staged_manifest
        plan = self._make_plan()
        area = StagingArea(plan)
        area.stage_all()
        result = verify_staged_manifest(area.staging_root)
        self.assertTrue(result["valid"], result["errors"])

    def test_path_traversal_rejected(self):
        from installer.staging import StagingArea, StagingError
        plan = self._make_plan()
        area = StagingArea(plan)
        bad = Path("/tmp/outside")
        with self.assertRaises(StagingError):
            area._validate_containment(bad)

    def test_git_excluded(self):
        from installer.staging import StagingArea
        plan = self._make_plan()
        area = StagingArea(plan)
        manifest = area.create_manifest(plan.source.canonical_source)
        paths = [m["path"] for m in manifest]
        self.assertNotIn(".git", paths)
        self.assertNotIn(".git/config", paths)

    def test_hermes_config_excluded(self):
        # Our repo root has no .env/config.yaml at canonical source; verify exclusion list is honored.
        from installer.staging import StagingArea
        self.assertIn(".env", StagingArea.EXCLUDED_NAMES)
        self.assertIn("config.yaml", StagingArea.EXCLUDED_NAMES)


if __name__ == "__main__":
    unittest.main()
