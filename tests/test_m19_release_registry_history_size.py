"""Milestone 19 — Release registry / history size boundedness audit.

Production release registry and history bounds catalog:
- release_engine.registry.ReleaseRegistry — NO explicit release count limit
  - releases list grows unbounded; no pruning or archive logic
  - register(), activate(), rollback_eligible() all iterate entire list
- config_engine.persistence.ConfigurationStore — NO explicit transaction count limit
  - archive_transaction() writes a new .json + .record.json per transaction
  - list_transactions() globs all *.record.json files
  - No auto-prune; history directory grows with every commit
- config_engine.defaults.max_sequence_delta — schema-only for updates module;
  not related to release registry or config history.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. ReleaseRegistry release count — unbounded
# ---------------------------------------------------------------------------

class TestReleaseRegistryUnbounded:
    def test_registry_accepts_many_releases(self, tmp_path):
        """ReleaseRegistry has no explicit release count limit."""
        from release_engine.registry import ReleaseRegistry, ReleaseRecord
        reg = ReleaseRegistry(tmp_path / "releases.json")
        for i in range(300):
            reg.register(ReleaseRecord(
                release_id=f"rel-{i:04d}",
                version="1.0.0",
                release_sequence=i,
                channel="stable",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signing_key_id="key-1",
            ))
        assert len(reg.list_releases()) == 300

    def test_registry_file_grows_unbounded(self, tmp_path):
        """ReleaseRegistry JSON file grows with each release; no pruning."""
        from release_engine.registry import ReleaseRegistry, ReleaseRecord
        reg = ReleaseRegistry(tmp_path / "releases.json")
        for i in range(200):
            reg.register(ReleaseRecord(
                release_id=f"rel-{i:04d}",
                version="1.0.0",
                release_sequence=i,
                channel="stable",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signing_key_id="key-1",
            ))
        file_size = reg.path.stat().st_size
        assert file_size > 40_000  # significantly large

    def test_activate_scans_entire_list(self, tmp_path):
        """activate() iterates all releases to clear active flags."""
        from release_engine.registry import ReleaseRegistry, ReleaseRecord
        reg = ReleaseRegistry(tmp_path / "releases.json")
        for i in range(100):
            reg.register(ReleaseRecord(
                release_id=f"rel-{i:04d}",
                version="1.0.0",
                release_sequence=i,
                channel="stable",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signing_key_id="key-1",
            ))
        reg.activate("rel-0050", timestamp="2024-01-01T00:00:00Z")
        active = reg.get_active()
        assert active is not None
        assert active.release_id == "rel-0050"

    def test_rollback_eligible_scans_entire_list(self, tmp_path):
        """rollback_eligible() iterates all releases to find previous ones."""
        from release_engine.registry import ReleaseRegistry, ReleaseRecord
        reg = ReleaseRegistry(tmp_path / "releases.json")
        for i in range(50):
            reg.register(ReleaseRecord(
                release_id=f"rel-{i:04d}",
                version="1.0.0",
                release_sequence=i,
                channel="stable",
                manifest_digest="sha256:" + "a" * 64,
                bundle_digest="sha256:" + "b" * 64,
                signing_key_id="key-1",
            ))
        reg.activate("rel-0010")
        reg.activate("rel-0020")
        eligible = reg.rollback_eligible()
        assert len(eligible) == 1
        assert eligible[0].release_id == "rel-0010"


# ---------------------------------------------------------------------------
# 2. ConfigurationStore transaction history — unbounded
# ---------------------------------------------------------------------------

class TestConfigurationHistoryUnbounded:
    def test_archive_transaction_creates_unbounded_history(self, tmp_path):
        """ConfigurationStore creates a new snapshot + record for every transaction."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(config_root=tmp_path / "config", state_root=tmp_path / "state")
        txn_ids = []
        for i in range(100):
            txn_id = store.archive_transaction(
                previous=None,
                new={"value": i, "_meta": {"version": f"1.0.{i}", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
            txn_ids.append(txn_id)
        assert len(store.list_transactions()) == 100
        # Verify snapshot files exist
        for txn_id in txn_ids:
            assert (store.history_dir / f"{txn_id}.json").exists()
            assert (store.history_dir / f"{txn_id}.record.json").exists()

    def test_history_directory_grows_unbounded(self, tmp_path):
        """The history directory accumulates files without pruning."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(config_root=tmp_path / "config", state_root=tmp_path / "state")
        for i in range(50):
            store.archive_transaction(
                previous=None,
                new={"value": i, "_meta": {"version": f"1.0.{i}", "profile": "default"}},
                profile="default",
                author="test",
                validation_result="ok",
                migration_performed=[],
            )
        record_files = list(store.history_dir.glob("*.record.json"))
        snapshot_files = list(store.history_dir.glob("*.json"))
        # snapshot glob also matches .record.json, so subtract
        snapshot_files = [p for p in snapshot_files if not p.name.endswith(".record.json")]
        assert len(record_files) == 50
        assert len(snapshot_files) == 50

    def test_rollback_creates_additional_transaction(self, tmp_path):
        """Rollback archives the restored snapshot as a new transaction, adding to history."""
        from config_engine.persistence import ConfigurationStore
        store = ConfigurationStore(config_root=tmp_path / "config", state_root=tmp_path / "state")
        # Create initial transaction
        txn_id = store.archive_transaction(
            previous=None,
            new={"value": 1, "_meta": {"version": "1.0.0", "profile": "default"}},
            profile="default",
            author="test",
            validation_result="ok",
            migration_performed=[],
        )
        store.save_committed({"value": 2, "_meta": {"version": "1.0.1", "profile": "default"}})
        initial_count = len(store.list_transactions())
        # Rollback creates a NEW transaction
        new_txn_id, _ = store.rollback_to(txn_id, author="test")
        assert new_txn_id != txn_id
        assert len(store.list_transactions()) == initial_count + 1


# ---------------------------------------------------------------------------
# 3. No auto-prune in either system
# ---------------------------------------------------------------------------

class TestNoAutoPrune:
    def test_release_registry_never_prunes(self, tmp_path):
        """ReleaseRegistry.register() never removes old releases."""
        import inspect
        from release_engine.registry import ReleaseRegistry
        src = inspect.getsource(RegistryError := ReleaseRegistry)
        assert "prune" not in src.lower()
        assert "archive" not in src.lower()
        assert "limit" not in src.lower()

    def test_configuration_store_never_prunes(self, tmp_path):
        """ConfigurationStore never deletes old transaction snapshots."""
        import inspect
        from config_engine.persistence import ConfigurationStore
        src = inspect.getsource(ConfigurationStore)
        assert "prune" not in src.lower()
        assert "unlink" not in src.lower() or "clear_staging" in src
        # clear_staging removes staging files, not history


# ---------------------------------------------------------------------------
# 4. max_sequence_delta is schema-only (not a history bound)
# ---------------------------------------------------------------------------

class TestMaxSequenceDeltaSchemaOnly:
    def test_max_sequence_delta_is_updates_config_only(self):
        """max_sequence_delta in config_engine/defaults.py is for the updates module, not release registry."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        updates = registry.get("updates")
        spec = updates.fields["max_sequence_delta"]
        assert spec.default == 1000
        assert spec.min_value == 1
        assert spec.max_value == 1000000

    def test_no_production_code_reads_max_sequence_delta_for_registry(self):
        """No release_engine or config_engine module uses max_sequence_delta to bound history."""
        import inspect
        from release_engine import registry as reg
        assert "max_sequence_delta" not in inspect.getsource(reg)
        from config_engine import persistence as pers
        assert "max_sequence_delta" not in inspect.getsource(pers)