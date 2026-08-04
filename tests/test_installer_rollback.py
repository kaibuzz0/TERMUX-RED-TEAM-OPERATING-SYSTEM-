"""Tests for activation rollback."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from installer.activate import ActiveState, ActivationSafetyError
from installer.plan import generate_plan
from installer.schema import ActivationState
from installer.staging import StagingArea


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _activate_two(self):
        plan1 = generate_plan(transaction_id="txn-rollback-1")
        area1 = StagingArea(plan1)
        staged1 = area1.stage_all()
        state = ActiveState(plan1.target.data_root, plan1.target.state_root, plan1.transaction_id)
        r1 = state.promote_to_ready(staged1, plan1)
        state.activate(r1.release_id, approve=True)

        plan2 = generate_plan(transaction_id="txn-rollback-2")
        area2 = StagingArea(plan2)
        staged2 = area2.stage_all()
        r2 = state.promote_to_ready(staged2, plan2)
        state.activate(r2.release_id, approve=True)
        return state, r1, r2

    def test_verified_previous_release_required(self):
        state, r1, r2 = self._activate_two()
        pointer = state.rollback(approve=True)
        self.assertEqual(pointer.active_release_id, r1.release_id)

    def test_unverified_previous_release_rejected(self):
        state, r1, r2 = self._activate_two()
        # Remove release1 metadata to simulate unverified previous
        state._release_metadata_path(r1.release_id).unlink()
        with self.assertRaises(ActivationSafetyError):
            state.rollback(approve=True)

    def test_rollback_preserves_failed_release(self):
        state, r1, r2 = self._activate_two()
        state.rollback(approve=True)
        r2_meta = state._read_release_metadata(r2.release_id)
        self.assertIn(r2_meta.state, (ActivationState.ROLLBACK_AVAILABLE,))
        self.assertTrue(state._release_path(r2.release_id).exists())

    def test_rollback_writes_journal(self):
        state, r1, r2 = self._activate_two()
        state.rollback(approve=True)
        journal_dir = state.state_root / "install-journal"
        files = list(journal_dir.glob("*.jsonl"))
        self.assertTrue(files)
        text = files[0].read_text(encoding="utf-8")
        self.assertIn("rollback", text)

    def test_no_user_data_changed(self):
        # No user data directory exists yet; rollback must not create arbitrary files outside state/data roots.
        state, r1, r2 = self._activate_two()
        before = set(self.tmp.rglob("*"))
        state.rollback(approve=True)
        after = set(self.tmp.rglob("*"))
        # Some journal/state files may appear, but no shell startup or boot files.
        new = after - before
        for p in new:
            self.assertNotIn(".bashrc", str(p))
            self.assertNotIn("Termux", str(p))
            self.assertTrue(
                str(p).startswith(str(state.data_root)) or str(p).startswith(str(state.state_root))
            )

    def test_rollback_requires_approval(self):
        state, r1, r2 = self._activate_two()
        with self.assertRaises(ActivationSafetyError):
            state.rollback(approve=False)

    def test_missing_previous_release_rejected(self):
        state, r1, r2 = self._activate_two()
        pointer = state._active_pointer()
        pointer.previous_release_id = ""
        state._write_active_pointer(pointer)
        with self.assertRaises(ActivationSafetyError):
            state.rollback(approve=True)

    def test_interrupted_rollback_recoverable(self):
        state, r1, r2 = self._activate_two()
        # Leave a stale lock from same transaction
        state._write_lock(r1.transaction_id)
        pointer = state.rollback(approve=True)
        self.assertEqual(pointer.active_release_id, r1.release_id)


if __name__ == "__main__":
    unittest.main()
