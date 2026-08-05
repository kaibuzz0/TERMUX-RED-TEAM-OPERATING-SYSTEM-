"""Tests for recovery helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from updates.recovery import diagnose, repair_stale_locks, RecoveryLevel


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_diagnose_non_mutating(self):
        result = diagnose(self.tmp)
        self.assertFalse(result["mutation"])

    def test_repair_stale_locks(self):
        import time
        lock = self.tmp / "active.lock"
        lock.write_text("x", encoding="utf-8")
        time.sleep(0.05)
        result = repair_stale_locks(self.tmp, max_age_seconds=0)
        self.assertTrue(result["mutation"])
        self.assertFalse(lock.exists())

    def test_recovery_levels(self):
        self.assertEqual(RecoveryLevel.DIAGNOSE.value, 0)
        self.assertEqual(RecoveryLevel.DESTRUCTIVE_RESET.value, 6)


if __name__ == "__main__":
    unittest.main()
