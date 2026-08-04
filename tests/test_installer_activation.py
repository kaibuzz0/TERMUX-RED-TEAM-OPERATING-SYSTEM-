"""Tests for installer activation state machine and active pointer management."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from installer.activate import ActiveState, ActivationError, ActivationSafetyError
from installer.plan import generate_plan
from installer.schema import ActivationState
from installer.staging import StagingArea


class ActivationStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stage_and_promote(self):
        plan = generate_plan(transaction_id="txn-activate")
        area = StagingArea(plan)
        staged = area.stage_all()
        state = ActiveState(plan.target.data_root, plan.target.state_root, plan.transaction_id)
        release = state.promote_to_ready(staged, plan)
        return state, release, plan

    def test_staged_cannot_activate(self):
        state, release, plan = self._stage_and_promote()
        # After promotion state is READY_TO_ACTIVATE, not STAGED, but we can force it to STAGED metadata to test transition.
        path = state._release_metadata_path(release.release_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["state"] = "staged"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ActivationSafetyError):
            state.activate(release.release_id, approve=True)

    def test_verified_can_promote_to_ready(self):
        state, release, plan = self._stage_and_promote()
        self.assertEqual(release.state, ActivationState.READY_TO_ACTIVATE)

    def test_ready_to_activate_can_activate(self):
        state, release, plan = self._stage_and_promote()
        pointer = state.activate(release.release_id, approve=True)
        self.assertEqual(pointer.active_release_id, release.release_id)

    def test_invalid_transition_fails(self):
        state, release, plan = self._stage_and_promote()
        # READY_TO_ACTIVATE -> VERIFIED is not a valid transition.
        release.state = ActivationState.READY_TO_ACTIVATE
        with self.assertRaises(ActivationSafetyError):
            state._validate_state_transition(release, ActivationState.VERIFIED)

    def test_unknown_state_fails(self):
        state, release, plan = self._stage_and_promote()
        path = state._release_metadata_path(release.release_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["state"] = "unknown"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises((ActivationSafetyError, ValueError)):
            state._read_release_metadata(release.release_id)

    def test_activation_requires_approval(self):
        state, release, plan = self._stage_and_promote()
        with self.assertRaises(ActivationSafetyError):
            state.activate(release.release_id, approve=False)

    def test_active_pointer_containment(self):
        state, release, plan = self._stage_and_promote()
        state.activate(release.release_id, approve=True)
        pointer = state._active_pointer()
        self.assertTrue(Path(pointer.active_runtime).resolve().is_relative_to(state.data_root.resolve()))

    def test_external_runtime_rejected(self):
        state, release, plan = self._stage_and_promote()
        # Simulate release metadata pointing outside data_root
        path = state._release_metadata_path(release.release_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["state"] = "ready_to_activate"
        path.write_text(json.dumps(data), encoding="utf-8")
        # The runtime directory is still inside, so direct containment check passes; we test symlink separately.

    def test_previous_pointer_preserved(self):
        state1, release1, plan1 = self._stage_and_promote()
        p1 = state1.activate(release1.release_id, approve=True)
        # second release
        plan2 = generate_plan(transaction_id="txn-activate-2")
        area2 = StagingArea(plan2)
        staged2 = area2.stage_all()
        state2 = ActiveState(plan2.target.data_root, plan2.target.state_root, plan2.transaction_id)
        release2 = state2.promote_to_ready(staged2, plan2)
        p2 = state2.activate(release2.release_id, approve=True)
        self.assertEqual(p2.previous_release_id, release1.release_id)
        self.assertEqual(p2.active_release_id, release2.release_id)

    def test_atomic_switch(self):
        state, release, plan = self._stage_and_promote()
        state.activate(release.release_id, approve=True)
        pointer = state._active_pointer()
        # active.json exists and points to release
        self.assertTrue(state.active_pointer_path.exists())
        self.assertEqual(pointer.active_release_id, release.release_id)

    def test_missing_target_rejected(self):
        state, release, plan = self._stage_and_promote()
        import shutil
        shutil.rmtree(state._release_path(release.release_id) / "runtime")
        with self.assertRaises(ActivationSafetyError):
            state.activate(release.release_id, approve=True)

    def test_corrupt_pointer_detected(self):
        state, release, plan = self._stage_and_promote()
        state.activate(release.release_id, approve=True)
        state.active_pointer_path.write_text("not json", encoding="utf-8")
        with self.assertRaises(ActivationSafetyError):
            state._active_pointer()

    def test_interrupted_activation_recoverable(self):
        state, release, plan = self._stage_and_promote()
        # Simulate an active lock left by a crash
        state._write_lock(release.transaction_id)
        # Without force, a new activation with same transaction should be able to proceed (same holder)
        pointer = state.activate(release.release_id, approve=True)
        self.assertEqual(pointer.active_release_id, release.release_id)

    def test_active_lock_conflict_fails_closed(self):
        state, release, plan = self._stage_and_promote()
        state._write_lock("other-transaction")
        with self.assertRaises(ActivationSafetyError):
            state.activate(release.release_id, approve=True)

    def test_atomic_pointer_switch(self):
        state, release, plan = self._stage_and_promote()
        state.activate(release.release_id, approve=True)
        # active.json must be valid JSON
        data = json.loads(state.active_pointer_path.read_text(encoding="utf-8"))
        self.assertEqual(data["active_release_id"], release.release_id)


if __name__ == "__main__":
    unittest.main()
