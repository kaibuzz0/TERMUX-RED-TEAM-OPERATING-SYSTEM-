"""Tests for vault secret set/get/list/remove."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from security.vault import Vault


class VaultOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)
        self.vault = Vault()
        self.vault.init("pw")
        self.vault.unlock("pw")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_set_and_get(self):
        self.vault.set("op.password", "secret", secret_type="password")
        self.assertEqual(self.vault.get("op.password").decode(), "secret")

    def test_list_without_values(self):
        self.vault.set("a", "1")
        records = self.vault.list(include_values=False)
        for r in records:
            self.assertNotIn("value", r)

    def test_remove(self):
        self.vault.set("a", "1")
        self.vault.remove("a")
        with self.assertRaises(Exception):
            self.vault.get("a")

    def test_duplicate_name_policy(self):
        self.vault.set("a", "1")
        self.vault.set("a", "2")
        self.assertEqual(self.vault.get("a").decode(), "2")

    def test_scope_enforcement_metadata(self):
        self.vault.set("svc", "x", scope="SERVICE")
        records = self.vault.list()
        self.assertEqual(records[0]["scope"], "SERVICE")

    def test_locked_vault_rejects_access(self):
        self.vault.set("a", "1")
        self.vault.save("pw")
        self.vault.lock()
        with self.assertRaises(Exception):
            self.vault.get("a")


if __name__ == "__main__":
    unittest.main()
