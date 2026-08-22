"""Tests for legacy installation detection and migration planning."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.legacy import detect_legacy_installation, build_migration_plan
from installer.schema import LegacyStatus


class LegacyDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_legacy_installation(self):
        nonexistent = self.tmp / "does_not_exist"
        result = detect_legacy_installation(legacy_root_override=nonexistent)
        self.assertEqual(result["legacy_status"], LegacyStatus.NO_LEGACY_INSTALLATION.value)

    def test_home_hive_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / "bin" / "hive").parent.mkdir(parents=True)
        (self.tmp / "hive" / "bin" / "hive").write_text("#!/bin/bash", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertEqual(result["legacy_status"], LegacyStatus.LEGACY_DETECTED.value)
        self.assertEqual(result["legacy_root"], str(self.tmp / "hive"))

    def test_legacy_root_fixture_detected(self):
        # Use override to simulate /root/hive without needing root
        legacy = self.tmp / "root-hive"
        legacy.mkdir()
        (legacy / "README").write_text("legacy", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=legacy)
        self.assertEqual(result["legacy_root"], str(legacy))
        self.assertIn(result["legacy_status"], (LegacyStatus.LEGACY_DETECTED.value, LegacyStatus.LEGACY_PARTIAL.value))

    def test_devai_install_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / "Hive Ops DevAI").mkdir()
        (self.tmp / "hive" / "Hive Ops DevAI" / "bin" / "hive").parent.mkdir(parents=True)
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertTrue(result["has_devai"])

    def test_final_tree_install_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / "Hive Ops Final").mkdir()
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertTrue(result["has_final"])

    def test_partial_install_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / "random.txt").write_text("x", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertEqual(result["legacy_status"], LegacyStatus.LEGACY_PARTIAL.value)

    def test_shell_startup_entries_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / ".bashrc").write_text("export HIVE=1", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertTrue(result["has_bashrc_modification"])

    def test_termux_boot_entries_detected(self):
        (self.tmp / "hive").mkdir()
        (self.tmp / "hive" / "termux-boot.sh").write_text("termux", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertTrue(result["has_boot_modification"])

    def test_base64_credential_detected(self):
        (self.tmp / "hive").mkdir(exist_ok=True)
        (self.tmp / "hive" / "auth.json").write_text("dXNlcjpwYXNzd29yZDEyMzQ1Njc4OQ==\n", encoding="utf-8")
        result = detect_legacy_installation(legacy_root_override=self.tmp / "hive")
        self.assertTrue(result["has_base64_credential"])

    def test_no_mutation_during_detection(self):
        before = set(self.tmp.rglob("*"))
        detect_legacy_installation(self.tmp)
        after = set(self.tmp.rglob("*"))
        self.assertEqual(before, after)

    @unittest.skipIf(os.name == "nt", "symlinks require elevated privileges on Windows")
    def test_root_bin_hive_symlink_detected(self):
        """/root/bin/hive symlink pointing to /root/Hive-Ops/bin/hive must be detected."""
        # Simulate /root on the temp filesystem.
        fake_root = self.tmp / "root"
        fake_root.mkdir()
        hive_ops = fake_root / "Hive-Ops"
        hive_ops.mkdir()
        (hive_ops / "bin" / "hive").parent.mkdir(parents=True)
        (hive_ops / "bin" / "hive").write_text("#!/bin/bash\nHIVE_HOME=/root/Hive-Ops", encoding="utf-8")

        bin_dir = fake_root / "bin"
        bin_dir.mkdir()
        (bin_dir / "hive").symlink_to(hive_ops / "bin" / "hive")

        import shutil
        original_which = shutil.which
        def fake_which(name):
            if name == "hive":
                return str(bin_dir / "hive")
            return original_which(name)

        with patch.object(shutil, "which", fake_which):
            result = detect_legacy_installation(legacy_root_override=None)

        self.assertNotEqual(
            result["legacy_status"],
            LegacyStatus.NO_LEGACY_INSTALLATION.value,
            f"Expected legacy detected but got: {result}",
        )

    def test_unrelated_hive_command_ignored(self):
        """An unrelated executable named hive must not trigger false migration."""
        fake_root = self.tmp / "root"
        fake_root.mkdir()
        bin_dir = fake_root / "bin"
        bin_dir.mkdir()
        (bin_dir / "hive").write_text("#!/bin/bash\necho hello", encoding="utf-8")

        import shutil
        original_which = shutil.which
        def fake_which(name):
            if name == "hive":
                return str(bin_dir / "hive")
            return original_which(name)

        with patch.object(shutil, "which", fake_which):
            result = detect_legacy_installation(legacy_root_override=None)

        self.assertEqual(result["legacy_status"], LegacyStatus.NO_LEGACY_INSTALLATION.value)

    @unittest.skipIf(os.name == "nt", "symlinks require elevated privileges on Windows")
    def test_broken_symlink_handled_safely(self):
        """A broken hive symlink must not crash detection."""
        fake_root = self.tmp / "root"
        fake_root.mkdir()
        bin_dir = fake_root / "bin"
        bin_dir.mkdir()
        (bin_dir / "hive").symlink_to("/nonexistent/path/hive")

        import shutil
        original_which = shutil.which
        def fake_which(name):
            if name == "hive":
                return str(bin_dir / "hive")
            return original_which(name)

        with patch.object(shutil, "which", fake_which):
            result = detect_legacy_installation(legacy_root_override=None)
        # Should not raise and should not falsely claim legacy.
        self.assertIn(
            result["legacy_status"],
            (LegacyStatus.NO_LEGACY_INSTALLATION.value, LegacyStatus.UNKNOWN.value),
        )


if __name__ == "__main__":
    unittest.main()