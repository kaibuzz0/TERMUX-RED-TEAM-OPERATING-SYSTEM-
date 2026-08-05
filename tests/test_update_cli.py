"""Tests for `hive update` and `hive recovery` CLI delegation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class UpdateCliTests(unittest.TestCase):
    def _run(self, args):
        env = dict()
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, str(REPO_ROOT / "bin" / "hive")] + args
        return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))

    def test_update_status(self):
        r = self._run(["update", "status"])
        self.assertEqual(r.returncode, 0)

    def test_update_check(self):
        r = self._run(["update", "check"])
        self.assertEqual(r.returncode, 0)

    def test_recovery_diagnose(self):
        with tempfile.TemporaryDirectory() as td:
            r = self._run(["recovery", "diagnose", "--release-root", td])
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
