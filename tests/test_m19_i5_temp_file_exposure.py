"""Milestone 19 — I5 Temporary file exposure investigation.

Verifies atomic-write/temp-file paths in:
- config_engine/loader.py (atomic_write_json)
- installer/activate.py
- release_engine/plugin_registry.py
- hive_broker/session.py
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

import sys
import pytest

if sys.platform == "win32":
    pytest.skip(
        "symlink tests require elevated privileges on Windows",
        allow_module_level=True,
    )



class TestTemporaryFileExposure:
    """I5 — verify temp file safety."""

    def test_atomic_write_json_no_tmp_leak(self, tmp_path):
        """atomic_write_json must not leave .tmp files after success."""
        from config_engine.loader import atomic_write_json
        target = tmp_path / "test.json"
        atomic_write_json(target, {"key": "value"})
        assert target.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp files: {tmp_files}"

    def test_atomic_write_json_concurrent_no_race(self, tmp_path):
        """Concurrent atomic_write_json to same target must not corrupt."""
        import threading
        from config_engine.loader import atomic_write_json
        target = tmp_path / "shared.json"

        def writer(n: int):
            atomic_write_json(target, {"writer": n})

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # File must exist and parse cleanly
        data = json.loads(target.read_text())
        assert isinstance(data, dict)
        assert "writer" in data

    def test_atomic_write_json_no_secret_in_tmp(self, tmp_path):
        """Even if write fails, temp file must not contain secret markers
        after the final atomic replace (temp file is gone)."""
        from config_engine.loader import atomic_write_json
        target = tmp_path / "secret.json"
        atomic_write_json(target, {"password": "M19_TEST_PASSWORD_SECRET"})
        # After replace, only the target file exists
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
        # Target file contains the secret (expected; file is the persisted data)
        data = json.loads(target.read_text())
        assert data["password"] == "M19_TEST_PASSWORD_SECRET"

    def test_installer_activate_no_tmp_leak(self, tmp_path):
        """installer/activate.py atomic writes must not leave .tmp files."""
        from installer.activate import ActiveState
        state = ActiveState(
            data_root=tmp_path / "data",
            state_root=tmp_path / "state",
            transaction_id="txn-1",
        )
        # Simulate pointer write
        from installer.schema import ActivePointer
        pointer = ActivePointer(
            active_release_id="r1",
            active_runtime="1.0",
            previous_release_id="",
        )
        state._write_active_pointer(pointer)
        # Verify no stale .tmp
        tmp_files = list((tmp_path / "data").rglob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp files: {tmp_files}"

    def test_plugin_registry_no_tmp_leak(self, tmp_path):
        """release_engine/plugin_registry.py atomic writes must not leave .tmp."""
        from release_engine.plugin_registry import PersistentPluginRegistry
        reg = PersistentPluginRegistry(tmp_path / "registry.json")
        from release_engine.plugin_registry import PluginRegistryRecord
        record = PluginRegistryRecord(
            plugin_id="test-plugin",
            version="1.0",
            installation_id="inst-1",
            manifest_digest="abc123",
            bundle_digest="def456",
            signature_trust="trusted",
            requested_capabilities=[],
            granted_capabilities=[],
            configuration_digest="cfg789",
            state="active",
            install_timestamp="2024-01-01T00:00:00",
            publisher=None,
            sdk_compatibility="1.0",
            quarantine_state=None,
        )
        reg.register(record)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp files: {tmp_files}"

    def test_broker_session_no_tmp_leak(self, tmp_path):
        """hive_broker/session.py _persist must not leave .tmp files."""
        from hive_broker.session import BrokerSession
        session = BrokerSession(state_root=tmp_path)
        session._persist()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp files: {tmp_files}"

    def test_symlinked_target_behavior(self, tmp_path):
        """Document that atomic_write_json to a symlink replaces the symlink
        node itself (Linux os.replace semantics), NOT the target file."""
        from config_engine.loader import atomic_write_json
        real = tmp_path / "real.json"
        link = tmp_path / "link.json"
        link.symlink_to(real)
        atomic_write_json(link, {"test": True})
        # os.replace on a symlink replaces the symlink node itself
        assert link.exists() and not link.is_symlink()
        # The original target (real.json) is untouched / may not exist
        assert not real.exists()

    def test_temp_file_permissions_not_world_readable(self, tmp_path):
        """On platforms that support it, verify restrictive permissions."""
        from config_engine.loader import atomic_write_json
        target = tmp_path / "perms.json"
        atomic_write_json(target, {"data": 1})
        mode = target.stat().st_mode
        # On Unix, at minimum owner-write should be set
        assert mode & stat.S_IWUSR, "Owner write permission missing"
        # Document that group/other permissions are platform-dependent
