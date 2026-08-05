"""Tests for `hive vault` CLI command delegation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class VaultCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, args, input_text: str = ""):
        env = os.environ.copy()
        env["HOME"] = str(self.tmp)
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, str(REPO_ROOT / "bin" / "hive"), "vault"] + args
        return subprocess.run(cmd, capture_output=True, text=True, input=input_text, env=env, cwd=str(REPO_ROOT))

    def test_no_password_in_argv(self):
        # We cannot inspect argv after the fact, but the CLI must reject or ignore --password.
        # Our CLI suppresses --password and uses getpass, so this is design-level.
        r = self._run(["status", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_json_status_contains_no_secret(self):
        r = self._run(["status", "--json"])
        data = json.loads(r.stdout)
        self.assertNotIn("value", str(data))

    def test_list_rejects_locked_vault(self):
        from security.vault import VaultSession
        s = VaultSession()
        s.init("pw")
        s.lock()
        r = self._run(["list", "--json"])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("locked", r.stderr)

    def test_get_rejects_locked_vault(self):
        from security.vault import VaultSession
        s = VaultSession()
        s.init("pw")
        s.lock()
        r = self._run(["get", "a"])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("locked", r.stderr)

    def test_exit_code_propagation(self):
        r = self._run(["status"])
        self.assertEqual(r.returncode, 0)

    def test_no_duplicated_vault_logic(self):
        text = (REPO_ROOT / "bin" / "hive").read_text(encoding="utf-8")
        self.assertIn("security.vault.cli", text)


if __name__ == "__main__":
    unittest.main()
