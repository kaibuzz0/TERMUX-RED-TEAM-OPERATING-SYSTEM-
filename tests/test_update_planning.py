"""Tests for update planning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from updates.planner import plan_update


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bundle = self.tmp / "bundle"
        self.bundle.mkdir()
        (self.bundle / "manifest.json").write_text('[{"path":"new.py","size":4,"sha256":"abc123"}]', encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plan_non_mutating(self):
        plan = plan_update(self.bundle, None)
        self.assertEqual(plan["added"], ["new.py"])
        self.assertEqual(plan["rollback_point"], None)


if __name__ == "__main__":
    unittest.main()
