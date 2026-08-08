"""Milestone 19 — Area F: Recovery guarantee tests.

Tests journal replay, rollback atomicity, restart backoff, and
config recovery after interruption.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from installer.journal import InstallJournal, JournalError
from config_engine.persistence import ConfigurationStore, atomic_write_json
from services.restart import RestartPolicy, ServiceRuntimeError


class TestRecoveryGuarantees:
    # -----------------------------------------------------------------------
    # F1: Journal replay after crash
    # -----------------------------------------------------------------------

    def test_journal_idempotent_entries(self):
        """F1: Journal entries must be idempotent (re-reading produces same records)."""
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            journal = InstallJournal(journal_dir, "txn-1")
            journal.start()
            journal.append("op-1", "write", {"path": "test"}, result="ok")
            journal.close("committed")

            # Read multiple times
            records1 = journal.read()
            records2 = journal.read()
            assert records1 == records2
            assert len(records1) == 3
            assert records1[-1]["operation_id"] == "close"

    def test_journal_survives_corrupted_line(self):
        """F1: Corrupted line in journal must raise JournalError, not silent skip."""
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            journal_file = journal_dir / "txn-corrupt.jsonl"
            journal_file.parent.mkdir(parents=True, exist_ok=True)
            journal_file.write_text(
                json.dumps({"sequence": 1, "operation_id": "start"}) + "\n"
                + "not valid json\n"
                + json.dumps({"sequence": 2, "operation_id": "close"}) + "\n",
                encoding="utf-8",
            )
            journal = InstallJournal(journal_dir, "txn-corrupt")
            with pytest.raises(JournalError, match="Corrupt journal line"):
                journal.read()

    def test_journal_is_complete_false_for_interrupted(self):
        """F1: Journal without close entry must report incomplete."""
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            journal = InstallJournal(journal_dir, "txn-incomplete")
            journal.start()
            journal.append("op-1", "write", {"path": "test"}, result="ok")
            # No close
            assert not journal.is_complete()
            records = journal.read()
            assert records[-1]["operation_id"] == "op-1"

    def test_journal_is_complete_true_for_closed(self):
        """F1: Journal with close entry must report complete."""
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            journal = InstallJournal(journal_dir, "txn-complete")
            journal.start()
            journal.close("committed")
            assert journal.is_complete()

    # -----------------------------------------------------------------------
    # F2: Rollback atomicity
    # -----------------------------------------------------------------------

    def test_rollback_restores_previous_config(self):
        """F2: Rollback must restore config to previous transaction state."""
        with tempfile.TemporaryDirectory() as tmp:
            config_root = Path(tmp) / "config"
            state_root = Path(tmp) / "state"
            store = ConfigurationStore(config_root, state_root)
            store.ensure_dirs()

            # Commit initial config and archive it
            initial = {"version": 1, "data": "initial"}
            store.save_committed(initial)
            initial_txn_id = store.archive_transaction(
                None, initial, profile="test", author="test",
                validation_result="ok", migration_performed=[]
            )

            # Modify committed config
            modified = {"version": 2, "data": "modified"}
            store.save_committed(modified)

            # Rollback should restore initial
            record_id, restored = store.rollback_to(initial_txn_id, author="test")
            committed = store.load_committed()
            assert committed == initial

    # -----------------------------------------------------------------------
    # F3: Config rollback completeness
    # -----------------------------------------------------------------------

    def test_rollback_completeness(self):
        """F3: Committed config after rollback must equal original snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            config_root = Path(tmp) / "config"
            state_root = Path(tmp) / "state"
            store = ConfigurationStore(config_root, state_root)
            store.ensure_dirs()

            # Original committed config
            original = {"version": 1, "settings": {"key": "value"}, "nested": {"a": 1}}
            store.save_committed(original)
            txn_id = store.archive_transaction(
                None, original, profile="test", author="test",
                validation_result="ok", migration_performed=[]
            )

            # Modify committed config
            modified = {"version": 2, "settings": {"key": "changed"}, "nested": {"a": 2}}
            store.save_committed(modified)

            # Rollback
            store.rollback_to(txn_id, author="test")

            committed = store.load_committed()
            assert committed == original
            # Verify deep equality
            assert committed["settings"]["key"] == "value"
            assert committed["nested"]["a"] == 1

    # -----------------------------------------------------------------------
    # F4: Service restart after crash
    # -----------------------------------------------------------------------

    def test_restart_backoff_increases(self):
        """F4: Restart delay must increase with each attempt."""
        policy = RestartPolicy({
            "restart": {
                "policy": "on-failure",
                "max_attempts": 5,
                "backoff_initial_seconds": 1,
                "backoff_max_seconds": 30,
            }
        })
        delays = []
        for _ in range(3):
            should, delay = policy.should_restart("svc-1", exit_code=1, manually_stopped=False)
            assert should is True
            delays.append(delay)
        # Delays should increase
        assert delays[0] < delays[1] < delays[2]

    def test_restart_crash_loop_detected(self):
        """F4: Crash loop must be detected after max_attempts."""
        policy = RestartPolicy({
            "restart": {
                "policy": "on-failure",
                "max_attempts": 3,
                "backoff_initial_seconds": 1,
                "window_seconds": 300,
            }
        })
        # Simulate 3 restarts
        for _ in range(3):
            should, delay = policy.should_restart("svc-1", exit_code=1, manually_stopped=False)
            assert should is True

        # 4th attempt should trigger crash loop
        with pytest.raises(ServiceRuntimeError, match="crash loop"):
            policy.should_restart("svc-1", exit_code=1, manually_stopped=False)

    def test_restart_window_reset(self):
        """F4: Stable window should reset attempt counter."""
        policy = RestartPolicy({
            "restart": {
                "policy": "on-failure",
                "max_attempts": 3,
                "window_seconds": 1,
                "backoff_initial_seconds": 1,
            }
        })
        # Use up attempts
        for _ in range(3):
            policy.should_restart("svc-1", exit_code=1, manually_stopped=False)

        # Wait for window to pass
        time.sleep(1.5)

        # Should be able to restart again (counter reset)
        should, delay = policy.should_restart("svc-1", exit_code=1, manually_stopped=False)
        assert should is True
        assert delay == 1.0  # Back to initial

    def test_manually_stopped_never_restarts(self):
        """F4: Manually stopped service must not restart."""
        policy = RestartPolicy({
            "restart": {
                "policy": "unless-stopped",
                "max_attempts": 5,
            }
        })
        should, delay = policy.should_restart("svc-1", exit_code=1, manually_stopped=True)
        assert should is False

    # -----------------------------------------------------------------------
    # F5: Vault persistence (no explicit backup mechanism exists)
    # -----------------------------------------------------------------------

    def test_vault_data_survives_config_changes(self):
        """F5: Vault state must be independent of config store."""
        with tempfile.TemporaryDirectory() as tmp:
            config_root = Path(tmp) / "config"
            state_root = Path(tmp) / "state"
            vault_root = Path(tmp) / "vault"
            vault_root.mkdir()

            # Simulate vault data
            vault_file = vault_root / "master.enc"
            vault_file.write_text("encrypted-data-here", encoding="utf-8")

            store = ConfigurationStore(config_root, state_root)
            store.ensure_dirs()

            # Multiple config changes
            store.save_committed({"v": 1})
            store.save_committed({"v": 2})
            store.save_committed({"v": 3})

            # Vault should survive
            assert vault_file.exists()
            assert vault_file.read_text(encoding="utf-8") == "encrypted-data-here"
