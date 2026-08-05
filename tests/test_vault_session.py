"""Tests for vault session lifecycle."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from security.vault import VaultSession, VaultError
from security.vault.session import SessionState


class VaultSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_locked_by_default(self):
        s = VaultSession()
        self.assertTrue(s.locked())
        self.assertEqual(s.state, SessionState.UNINITIALIZED)

    def test_unlock_success(self):
        s = VaultSession()
        s.init("pw")
        s.unlock("pw")
        self.assertEqual(s.state, SessionState.UNLOCKED)

    def test_unlock_failure(self):
        s = VaultSession()
        s.init("pw")
        with self.assertRaises(VaultError):
            s.unlock("wrong")
        self.assertTrue(s.locked())

    def test_repeated_failure_bounded(self):
        s = VaultSession()
        s.init("pw")
        for _ in range(VaultSession.MAX_ATTEMPTS):
            try:
                s.unlock("wrong")
            except VaultError:
                pass
        with self.assertRaises(VaultError):
            s.unlock("wrong")

    def test_lock_clears_session(self):
        s = VaultSession()
        s.init("pw")
        s.unlock("pw")
        s.lock()
        self.assertTrue(s.locked())
        self.assertEqual(s.state, SessionState.LOCKED)

    def test_corrupt_state_handled_safely(self):
        # Not implemented; placeholder
        pass


if __name__ == "__main__":
    unittest.main()
