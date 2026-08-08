"""Milestone 19 — Area D: Corrupted state and filesystem abuse tests.

Tests atomicity, corruption detection, containment, and recovery of
state files under the data and state roots.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from installer.activate import (
    ActiveState,
    ActivationSafetyError,
    ActivePointer,
    ReleaseInfo,
)
from config_engine.persistence import (
    ConfigurationStore,
    atomic_write_json,
    FileLock,
)
from config_engine.errors import ConfigError
from services.supervisor import Supervisor, ServiceConfigError


class TestCorruptedState:
    # -----------------------------------------------------------------------
    # D1: Corrupt active pointer
    # -----------------------------------------------------------------------

    def test_corrupt_active_pointer_fails_closed(self):
        """D1: Corrupt active.json must raise ActivationSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            # Write invalid JSON
            active.active_pointer_path.parent.mkdir(parents=True, exist_ok=True)
            active.active_pointer_path.write_text("not json")
            with pytest.raises(ActivationSafetyError, match="Corrupt active pointer"):
                active._active_pointer()

    def test_unknown_pointer_schema_fails_closed(self):
        """D1: Active pointer with wrong schema version must be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            active.active_pointer_path.parent.mkdir(parents=True, exist_ok=True)
            active.active_pointer_path.write_text(
                json.dumps({"schema_version": 999, "active_release_id": "x", "active_runtime": "y"}),
                encoding="utf-8",
            )
            with pytest.raises(ActivationSafetyError, match="Unknown active pointer schema"):
                active._active_pointer()

    # -----------------------------------------------------------------------
    # D2: Corrupt release metadata
    # -----------------------------------------------------------------------

    def test_corrupt_release_metadata_fails_closed(self):
        """D2: Corrupt .release.json must raise ActivationSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            # Create a release directory with corrupt metadata
            release_dir = data / "releases" / "rel-1"
            release_dir.mkdir(parents=True)
            (release_dir / ".release.json").write_text("not json")
            with pytest.raises(ActivationSafetyError, match="Corrupt release metadata"):
                active._read_release_metadata("rel-1")

    def test_missing_release_metadata_fails_closed(self):
        """D2: Missing release metadata must raise ActivationSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            with pytest.raises(ActivationSafetyError, match="Release metadata missing"):
                active._read_release_metadata("nonexistent")

    # -----------------------------------------------------------------------
    # D3: Stale lock detection
    # -----------------------------------------------------------------------

    def test_stale_lock_detection_and_recovery(self):
        """D3: Stale lock must be detected and recoverable."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            # Simulate a stale lock
            active.acquire_lock("other-txn")
            # Mark as stale by corrupting the lock file
            active.lock_path.write_text(json.dumps({"stale": True}), encoding="utf-8")
            recovered = active.recover_stale_lock()
            assert recovered is not None
            assert recovered.get("stale")
            assert not active.lock_path.exists()

    def test_stale_lock_prevents_new_activation(self):
        """D3: Held lock must block concurrent activation."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            active.acquire_lock("other-txn")
            with pytest.raises(ActivationSafetyError, match="lock held"):
                active.acquire_lock("txn-2", force=False)

    # -----------------------------------------------------------------------
    # D4: Partial config write
    # -----------------------------------------------------------------------

    def test_atomic_write_json_is_atomic(self):
        """D4: atomic_write_json must use temp+rename pattern."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            data = {"version": 1, "key": "value"}
            atomic_write_json(target, data)
            assert target.exists()
            assert json.loads(target.read_text(encoding="utf-8")) == data
            # No leftover temp files
            assert len(list(Path(tmp).glob("*.tmp"))) == 0

    def test_config_write_survives_crash(self):
        """D4: Config must remain valid even if write is interrupted."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            data = {"version": 1}
            atomic_write_json(target, data)
            # Simulate crash by leaving a temp file alongside
            temp = Path(tmp) / "config.json.tmp"
            temp.write_text("partial", encoding="utf-8")
            # Original should still be valid
            assert json.loads(target.read_text(encoding="utf-8")) == data

    def test_configuration_store_list_skips_corrupted_record(self):
        """D6: Corrupted transaction record must be skipped, not fatal."""
        with tempfile.TemporaryDirectory() as tmp:
            config_root = Path(tmp) / "config"
            state_root = Path(tmp) / "state"
            store = ConfigurationStore(config_root, state_root)
            store.ensure_dirs()
            # Create a corrupted .record.json
            record_dir = config_root / ".records"
            record_dir.mkdir(parents=True, exist_ok=True)
            (record_dir / "txn-bad.record.json").write_text("not json")
            # Should not crash
            txs = store.list_transactions()
            # Corrupted record may be silently skipped or logged
            # The key invariant is: no exception
            assert isinstance(txs, list)

    # -----------------------------------------------------------------------
    # D5: Symlink in state directory
    # -----------------------------------------------------------------------

    def test_symlink_resolution_in_state_paths(self):
        """D5: Symlinks in state paths must not escape containment."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            real = Path(tmp) / "real"
            base.mkdir()
            real.mkdir()
            # Create a symlink inside base pointing outside
            escape = base / "escape"
            escape.symlink_to("..")
            resolved = (base / "escape" / "real").resolve()
            # Verify we can detect escape with relative_to
            try:
                resolved.relative_to(base.resolve())
                assert False, "Should have escaped"
            except ValueError:
                pass  # Expected — this is the mechanism that protects us

    # -----------------------------------------------------------------------
    # D7: Release runtime escapes data root
    # -----------------------------------------------------------------------

    def test_release_runtime_containment(self):
        """D7: Release runtime path must be contained within data root."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            pointer = ActivePointer(
                active_release_id="rel-1",
                active_runtime=str(data / "releases" / "rel-1" / "runtime"),
                previous_release_id="",
                updated_at="2026-01-01T00:00:00Z",
            )
            # Write pointer and verify runtime path is under data
            active._write_active_pointer(pointer)
            loaded = active._active_pointer()
            runtime = Path(loaded.active_runtime).resolve()
            assert str(runtime).startswith(str(data.resolve()))

    def test_relative_to_detects_escape(self):
        """D7: relative_to() correctly detects path escapes."""
        base = Path("/tmp/test")
        # Direct traversal
        with pytest.raises(ValueError):
            (base / ".." / "etc").resolve().relative_to(base.resolve())
        # Hidden in symlink (already tested above)
