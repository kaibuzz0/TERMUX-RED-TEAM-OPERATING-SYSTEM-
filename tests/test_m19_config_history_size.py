"""Milestone 19 — Configuration history boundedness audit.

Production configuration history bounds catalog:
- config_engine.persistence.ConfigurationStore — NO explicit transaction count limit
  - archive_transaction() writes a new .json snapshot + .record.json per transaction
  - list_transactions() globs all *.record.json with no pagination or limit
  - rollback_to() archives the restored snapshot as a NEW transaction, adding to history
  - No auto-prune; history directory grows indefinitely
- config_engine.persistence.atomic_write_json — bounded by available disk space only
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. archive_transaction creates unbounded history
# ---------------------------------------------------------------------------

class TestArchiveTransactionUnbounded:
    def test_archive_transaction_accepts_many_transactions(self, tmp_path):
        """ConfigurationStore.archive_transaction() has no explicit limit."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        txn_ids = []
        for i in range(200):
            txn_id = store.archive_transaction(
                previous=None,
                new={"value": i, "_meta": {"version": f"1.0.{i}", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
            txn_ids.append(txn_id)
        assert len(txn_ids) == 200
        assert len(store.list_transactions()) == 200

    def test_each_transaction_creates_two_files(self, tmp_path):
        """Every transaction produces one .json snapshot + one .record.json."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        txn_id = store.archive_transaction(
            previous=None,
            new={"value": 1, "_meta": {"version": "1.0.0", "profile": "default"}},
            profile="default",
            author="test",
            validation_result="ok",
            migration_performed=[],
        )
        assert (store.history_dir / f"{txn_id}.json").exists()
        assert (store.history_dir / f"{txn_id}.record.json").exists()

    def test_history_directory_grows_with_every_commit(self, tmp_path):
        """The history directory accumulates files linearly with commits."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        for i in range(50):
            store.archive_transaction(
                previous=None,
                new={"value": i, "_meta": {"version": f"1.0.{i}", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
        json_files = [p for p in store.history_dir.glob("*.json") if not p.name.endswith(".record.json")]
        record_files = list(store.history_dir.glob("*.record.json"))
        assert len(json_files) == 50
        assert len(record_files) == 50


# ---------------------------------------------------------------------------
# 2. list_transactions loads all records
# ---------------------------------------------------------------------------

class TestListTransactionsUnbounded:
    def test_list_transactions_returns_all_records(self, tmp_path):
        """list_transactions() globs and loads every record file."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        for i in range(75):
            store.archive_transaction(
                previous=None,
                new={"value": i, "_meta": {"version": f"1.0.{i}", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
        all_records = store.list_transactions()
        assert len(all_records) == 75
        # All records should have a transaction_id and timestamp
        for r in all_records:
            assert "transaction_id" in r
            assert "timestamp" in r

    def test_list_transactions_no_pagination(self, tmp_path):
        """list_transactions() has no offset/limit parameters."""
        import inspect
        from config_engine.persistence import ConfigurationStore
        sig = inspect.signature(ConfigurationStore.list_transactions)
        assert list(sig.parameters.keys()) == ["self"]


# ---------------------------------------------------------------------------
# 3. rollback_to adds a new transaction
# ---------------------------------------------------------------------------

class TestRollbackAddsTransaction:
    def test_rollback_creates_new_transaction_record(self, tmp_path):
        """Rollback archives the restored snapshot as a new transaction."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        original_txn = store.archive_transaction(
            previous=None,
            new={"value": 1, "_meta": {"version": "1.0.0", "profile": "default"}},
            profile="default",
            author="test",
            validation_result="ok",
            migration_performed=[],
        )
        store.save_committed({"value": 2, "_meta": {"version": "1.0.1", "profile": "default"}})
        initial_count = len(store.list_transactions())
        new_txn, restored = store.rollback_to(original_txn, author="test")
        assert new_txn != original_txn
        assert len(store.list_transactions()) == initial_count + 1
        assert restored["value"] == 1

    def test_multiple_rollbacks_all_preserved(self, tmp_path):
        """Multiple successive rollbacks are all preserved in history."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        txn_a = store.archive_transaction(
            previous=None,
            new={"value": 1, "_meta": {"version": "1.0.0", "profile": "default"}},
            profile="default",
            author="test",
            validation_result="ok",
            migration_performed=[],
        )
        txn_b = store.archive_transaction(
            previous=None,
            new={"value": 2, "_meta": {"version": "1.0.1", "profile": "default"}},
            profile="default",
            author="test",
            validation_result="ok",
            migration_performed=[],
        )
        store.save_committed({"value": 3, "_meta": {"version": "1.0.2", "profile": "default"}})
        store.rollback_to(txn_a, author="test")
        store.rollback_to(txn_b, author="test")
        assert len(store.list_transactions()) == 4  # a, b, rollback_a, rollback_b


# ---------------------------------------------------------------------------
# 4. No auto-prune logic
# ---------------------------------------------------------------------------

class TestNoAutoPrune:
    def test_archive_transaction_never_deletes_old_records(self, tmp_path):
        """archive_transaction() never removes prior snapshot or record files."""
        import inspect
        from config_engine.persistence import ConfigurationStore
        src = inspect.getsource(ConfigurationStore.archive_transaction)
        assert "unlink" not in src
        assert "remove" not in src
        assert "prune" not in src.lower()
        assert "delete" not in src.lower()

    def test_list_transactions_never_deletes(self, tmp_path):
        """list_transactions() is read-only; no side effects."""
        import inspect
        from config_engine.persistence import ConfigurationStore
        src = inspect.getsource(ConfigurationStore.list_transactions)
        assert "unlink" not in src
        assert "remove" not in src

    def test_rollback_to_never_deletes(self, tmp_path):
        """rollback_to() never deletes old transactions."""
        import inspect
        from config_engine.persistence import ConfigurationStore
        src = inspect.getsource(ConfigurationStore.rollback_to)
        assert "unlink" not in src
        assert "remove" not in src
        assert "prune" not in src.lower()


# ---------------------------------------------------------------------------
# 5. committed config is single-file and bounded
# ---------------------------------------------------------------------------

class TestCommittedConfigBounded:
    def test_save_committed_overwrites_single_file(self, tmp_path):
        """save_committed() writes exactly one file; history is separate."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        store.save_committed({"version": "1.0.0"})
        assert store.committed_path.exists()
        first_mtime = store.committed_path.stat().st_mtime
        store.save_committed({"version": "1.0.1"})
        second_mtime = store.committed_path.stat().st_mtime
        assert second_mtime >= first_mtime
        # Still only one committed file
        assert len(list(store.config_root.glob("*.json"))) == 1

    def test_load_committed_returns_latest(self, tmp_path):
        """load_committed() returns the most recently saved configuration."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        store.save_committed({"version": "1.0.0"})
        store.save_committed({"version": "1.0.1"})
        loaded = store.load_committed()
        assert loaded["version"] == "1.0.1"


# ---------------------------------------------------------------------------
# 6. Transaction ID uniqueness
# ---------------------------------------------------------------------------

class TestTransactionIdUniqueness:
    def test_transaction_ids_are_unique(self, tmp_path):
        """archive_transaction generates unique txn IDs (UUID4-based)."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(
            config_root=tmp_path / "config",
            state_root=tmp_path / "state",
        )
        ids = set()
        for _ in range(100):
            txn_id = store.archive_transaction(
                previous=None,
                new={"value": 1, "_meta": {"version": "1.0.0", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
            assert txn_id not in ids
            ids.add(txn_id)
        assert len(ids) == 100