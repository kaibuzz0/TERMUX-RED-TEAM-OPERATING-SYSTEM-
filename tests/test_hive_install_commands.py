"""Tests for `hive install` dispatcher commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class HiveInstallCommandsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, args):
        env = os.environ.copy()
        env["HOME"] = str(self.tmp)
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, str(REPO_ROOT / "bin" / "hive"), "install"] + args
        return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))

    def test_hive_install_status(self):
        r = self._run(["status", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn("data_root", data)

    def test_hive_install_plan(self):
        r = self._run(["plan", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn("transaction_id", data)

    def test_hive_install_activate_requires_approval(self):
        # First stage
        r1 = self._run(["stage", "--json"])
        self.assertEqual(r1.returncode, 0, r1.stderr)
        staged = json.loads(r1.stdout)["staged_root"]
        r2 = self._run(["activate", staged, "--json"])
        # Without --approve should fail
        self.assertNotEqual(r2.returncode, 0)

    def test_json_output(self):
        r = self._run(["check", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn("existing_installation", data)

    def test_exit_code_propagation(self):
        r = self._run(["status"])
        self.assertEqual(r.returncode, 0)

    def test_no_duplicated_installer_logic(self):
        # bin/hive should import/run installer.install, not reimplement it.
        text = (REPO_ROOT / "bin" / "hive").read_text(encoding="utf-8")
        self.assertIn("installer.install", text)


if __name__ == "__main__":
    unittest.main()
