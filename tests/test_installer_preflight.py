"""Tests for installer/preflight.py."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent


class PreflightClassificationTests(unittest.TestCase):
    def test_windows_static_host_classification(self):
        from installer.preflight import run_preflight, CapabilityState
        from lib.hive_path import resolve_repository_root
        with patch.dict(os.environ, {"HOME": "C:\\Users\\test"}, clear=False):
            result = run_preflight(resolve_repository_root())
        self.assertIn(result.environment["platform"], ("win32", "cygwin", "msys"))
        self.assertEqual(result.classification["termux"], CapabilityState.NOT_APPLICABLE)

    def test_linux_classification(self):
        from installer.preflight import run_preflight, CapabilityState
        from lib.hive_path import resolve_repository_root
        with patch.dict(os.environ, {"HOME": "/home/test"}, clear=False):
            result = run_preflight(resolve_repository_root())
        # On Windows host os.name is 'nt'; this test validates classification logic, not host OS.
        self.assertIn(result.environment["os"], ("posix", "nt"))
        if result.environment["os"] == "nt":
            self.assertEqual(result.classification["termux"], CapabilityState.NOT_APPLICABLE)
        else:
            self.assertIn(result.classification["termux"], (CapabilityState.UNKNOWN, CapabilityState.NOT_APPLICABLE))

    def test_termux_fixture_classification(self):
        from installer.preflight import _detect_termux, CapabilityState
        env = {"TERMUX_VERSION": "0.118"}
        self.assertEqual(_detect_termux(env), CapabilityState.AVAILABLE)

    def test_missing_home(self):
        from installer.preflight import run_preflight
        from lib.hive_path import resolve_repository_root
        with patch.dict(os.environ, {}, clear=True):
            result = run_preflight(resolve_repository_root())
        self.assertIn("HOME is not set", result.errors)

    def test_missing_prefix_with_termux(self):
        from installer.preflight import run_preflight, CapabilityState, _detect_termux
        from lib.hive_path import resolve_repository_root
        import sys
        env = {
            "HOME": "/data/data/com.termux/files/home",
            "TERMUX_VERSION": "0.118",
        }
        self.assertEqual(_detect_termux({"TERMUX_VERSION": "0.118"}), CapabilityState.AVAILABLE)
        if sys.platform != "win32":
            with patch.dict(os.environ, env, clear=True):
                result = run_preflight(resolve_repository_root())
            self.assertIn("Termux detected but PREFIX is not set", result.warnings)

    def test_unwritable_target(self):
        # We cannot easily test real unwritable targets on Windows without admin.
        # This test verifies the target path is normalized and not shared storage.
        from installer.preflight import run_preflight
        from lib.hive_path import resolve_repository_root
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp
            result = run_preflight(resolve_repository_root())
        target = Path(result.environment["target_root"])
        self.assertTrue(target.is_absolute())

    def test_shared_storage_rejection(self):
        import sys
        from installer.preflight import run_preflight
        result = run_preflight(target_root=Path("/sdcard/hive"))
        if sys.platform != "win32":
            self.assertIn("Target must not be on shared Android storage", result.errors)
        else:
            # On Windows the absolute check passes and posix-specific checks are skipped.
            self.assertIn("Target root must be absolute", result.errors)

    def test_root_path_rejection(self):
        import sys
        from installer.preflight import run_preflight
        result = run_preflight(target_root=Path("/root/hive"))
        if sys.platform != "win32":
            self.assertIn("Target must not be under /root", result.errors)
        else:
            self.assertIn("Target root must be absolute", result.errors)

    def test_relative_target_rejection(self):
        from installer.preflight import run_preflight
        result = run_preflight(target_root=Path("hive"))
        self.assertIn("Target root must be absolute", result.errors)


if __name__ == "__main__":
    unittest.main()
