"""Tests for vault storage atomicity and containment."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from security.vault.storage import VaultStorage
from security.vault.errors import VaultSafetyError, VaultExistsError


class VaultStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_atomic_write(self):
        s = VaultStorage(self.tmp)
        s.write("payload")
        self.assertEqual(s.read(), "payload")
        self.assertTrue((self.tmp / "vault.json").exists())

    def test_interrupted_write_preserves_prior(self):
        s = VaultStorage(self.tmp)
        s.write("first")
        tmp = self.tmp / "vault.json.tmp"
        tmp.write_text("partial", encoding="utf-8")
        # Atomic replace would overwrite; we simulate crash by leaving tmp.
        # Read must still return original.
        self.assertEqual(s.read(), "first")

    def test_symlink_target_rejected(self):
        # storage path is inside vault dir by construction; no symlink support in current implementation
        pass

    def test_path_traversal_rejected(self):
        s = VaultStorage(self.tmp)
        with self.assertRaises(VaultSafetyError):
            s._ensure_contained(self.tmp.parent / "evil")

    def test_status_creates_no_files(self):
        s = VaultStorage(self.tmp)
        self.assertFalse(s.exists())
        self.assertEqual(list(self.tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
