"""Tests for legacy credential detection and migration planning."""

from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path

from security.vault.migration import detect_legacy_credentials, build_migration_plan


class CredentialMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_legacy(self):
        result = detect_legacy_credentials()
        self.assertFalse(result["legacy_detected"])

    def test_base64_legacy_file_detected(self):
        auth_dir = self.tmp / ".hive_auth"
        auth_dir.mkdir()
        (auth_dir / "passwd").write_text(base64.b64encode(b"pass\npin").decode(), encoding="utf-8")
        result = detect_legacy_credentials()
        self.assertTrue(result["legacy_detected"])
        self.assertEqual(result["storage_format"], "base64")

    def test_migration_plan_non_mutating(self):
        auth_dir = self.tmp / ".hive_auth"
        auth_dir.mkdir()
        (auth_dir / "passwd").write_text(base64.b64encode(b"pass\npin").decode(), encoding="utf-8")
        plan = build_migration_plan()
        self.assertTrue(plan["can_migrate"])
        self.assertFalse(plan["auto_delete_original"])
        # Original still there
        self.assertTrue((self.tmp / ".hive_auth" / "passwd").exists())

    def test_unknown_legacy_format_rejected(self):
        auth_dir = self.tmp / ".hive_auth"
        auth_dir.mkdir()
        (auth_dir / "passwd").write_text("not-base64", encoding="utf-8")
        result = detect_legacy_credentials()
        self.assertEqual(result["storage_format"], "unknown")


if __name__ == "__main__":
    unittest.main()
