"""Tests for concurrent registry writes — documents last-write-wins behavior."""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

import sys
import multiprocessing

import sys
import multiprocessing

import pytest

# These tests use multiprocessing with local closures as worker targets. On
# Windows the default start method is 'spawn', which requires worker targets to
# be picklable/top-level. The local closures cannot be spawned, so the suite is
# skipped on win32+spawn until the workers are refactored to module-level
# functions (see HRA-004).
if sys.platform == "win32" and multiprocessing.get_start_method() == "spawn":
    pytest.skip(
        "multiprocessing tests require fork or top-level workers (Windows spawn incompatible)",
        allow_module_level=True,
    )


class TestConcurrentRegistryWrites:
    def test_two_registry_writers_concurrently(self):
        """A1/A5: Two processes write to PersistentPluginRegistry simultaneously.

        FileLock serializes mutations. With distinct plugin IDs, both survive.
        With same plugin ID, exactly one wins; the other sees the committed
        state inside the lock and raises RegistryError (already registered).
        """
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            def _worker_write(registry_path: str, plugin_id: str, version: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
                registry = PersistentPluginRegistry(Path(registry_path))
                record = PluginRegistryRecord(
                    plugin_id=plugin_id,
                    version=version,
                    installation_id=f"inst-{plugin_id}",
                    manifest_digest="sha256:aaa",
                    bundle_digest="sha256:bbb",
                    signature_trust="trusted",
                    requested_capabilities=[],
                    granted_capabilities=[],
                    configuration_digest="sha256:ccc",
                    state="installed",
                    install_timestamp="2026-01-01T00:00:00Z",
                    publisher=None,
                    sdk_compatibility="1.0",
                    quarantine_state=None,
                )
                try:
                    registry.register(record)
                    q.put(("registered", plugin_id))
                except Exception as e:
                    q.put(("error", plugin_id, str(e)))

            # Two workers with SAME plugin ID → exactly one winner
            p1 = multiprocessing.Process(
                target=_worker_write, args=(str(registry_path), "plugin-a", "1.0.0", q)
            )
            p2 = multiprocessing.Process(
                target=_worker_write, args=(str(registry_path), "plugin-a", "2.0.0", q)
            )
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            registered = [e for e in events if e[0] == "registered"]
            errors = [e for e in events if e[0] == "error"]

            # Exactly one registered; the other saw duplicate inside lock
            assert len(registered) == 1, f"Expected exactly 1 winner, got {registered}"
            assert len(errors) == 1, f"Expected exactly 1 duplicate error, got {errors}"
            assert "already registered" in errors[0][2]

            # File valid
            assert registry_path.exists()
            import json
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            assert "plugins" in data
            assert data["plugins"]["plugin-a"]["version"] in {"1.0.0", "2.0.0"}

    def test_registry_register_loser_fails_cleanly(self):
        """A1/A5: The losing concurrent register() call must fail with a
        clean, actionable exception — not crash, hang, or silently lose data."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord, RegistryError

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            def _worker(registry_path: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord, RegistryError
                registry = PersistentPluginRegistry(Path(registry_path))
                record = PluginRegistryRecord(
                    plugin_id="plugin-z",
                    version="1.0.0",
                    installation_id="inst-z",
                    manifest_digest="sha256:aaa",
                    bundle_digest="sha256:bbb",
                    signature_trust="trusted",
                    requested_capabilities=[],
                    granted_capabilities=[],
                    configuration_digest="sha256:ccc",
                    state="installed",
                    install_timestamp="2026-01-01T00:00:00Z",
                    publisher=None,
                    sdk_compatibility="1.0",
                    quarantine_state=None,
                )
                try:
                    registry.register(record)
                    q.put(("ok", None))
                except RegistryError as e:
                    q.put(("registry_error", str(e)))
                except Exception as e:
                    q.put(("unexpected", type(e).__name__, str(e)))

            # Pre-populate so the worker hits duplicate immediately
            registry = PersistentPluginRegistry(registry_path)
            existing = PluginRegistryRecord(
                plugin_id="plugin-z",
                version="0.9.0",
                installation_id="inst-z-old",
                manifest_digest="sha256:old",
                bundle_digest="sha256:old",
                signature_trust="trusted",
                requested_capabilities=[],
                granted_capabilities=[],
                configuration_digest="sha256:old",
                state="installed",
                install_timestamp="2026-01-01T00:00:00Z",
                publisher=None,
                sdk_compatibility="1.0",
                quarantine_state=None,
            )
            registry.register(existing)

            p = multiprocessing.Process(target=_worker, args=(str(registry_path), q))
            p.start()
            p.join(timeout=10)
            assert not p.is_alive()

            ev = q.get(timeout=5)
            # Must be a clean RegistryError, not a generic Exception
            assert ev[0] == "registry_error", f"Expected RegistryError, got {ev}"
            assert "already registered" in ev[1].lower(), f"Message not actionable: {ev[1]}"

            # Existing record untouched
            import json
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            assert data["plugins"]["plugin-z"]["version"] == "0.9.0"

    def test_no_torn_json_under_concurrent_writes(self):
        """A1/A5: Concurrent writes must never leave torn / partial JSON.

        _save() writes to a temp file then replaces atomically. This test
        hammers the registry with concurrent writers and a background reader
        that repeatedly loads the file, verifying every snapshot is valid
        JSON and has the required schema keys.
        """
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            def _writer(registry_path: str, plugin_id: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
                registry = PersistentPluginRegistry(Path(registry_path))
                record = PluginRegistryRecord(
                    plugin_id=plugin_id,
                    version="1.0.0",
                    installation_id=f"inst-{plugin_id}",
                    manifest_digest="sha256:aaa",
                    bundle_digest="sha256:bbb",
                    signature_trust="trusted",
                    requested_capabilities=[],
                    granted_capabilities=[],
                    configuration_digest="sha256:ccc",
                    state="installed",
                    install_timestamp="2026-01-01T00:00:00Z",
                    publisher=None,
                    sdk_compatibility="1.0",
                    quarantine_state=None,
                )
                try:
                    registry.register(record)
                    q.put(("ok", plugin_id))
                except Exception as e:
                    q.put(("error", plugin_id, str(e)))

            def _reader(registry_path: str, iterations: int, q):
                from pathlib import Path
                import json
                import time
                p = Path(registry_path)
                for _ in range(iterations):
                    if p.exists():
                        try:
                            data = json.loads(p.read_text(encoding="utf-8"))
                            assert "schema_version" in data
                            assert "plugins" in data
                            assert isinstance(data["plugins"], dict)
                        except (json.JSONDecodeError, AssertionError) as e:
                            q.put(("torn", str(e)))
                            return
                    time.sleep(0.01)
                q.put(("clean", iterations))

            writers = []
            for i in range(6):
                p = multiprocessing.Process(
                    target=_writer, args=(str(registry_path), f"plugin-{i}", q)
                )
                writers.append(p)

            reader = multiprocessing.Process(
                target=_reader, args=(str(registry_path), 200, q)
            )

            reader.start()
            for w in writers:
                w.start()
            for w in writers:
                w.join(timeout=15)
            reader.join(timeout=5)

            assert not reader.is_alive(), "Reader timed out — possible deadlock"

            results = []
            while not q.empty():
                results.append(q.get_nowait())

            torn = [r for r in results if r[0] == "torn"]
            clean = [r for r in results if r[0] == "clean"]
            errors = [r for r in results if r[0] == "error"]

            assert len(torn) == 0, f"Torn JSON detected: {torn}"
            assert len(clean) == 1, "Reader should report clean completion"
            assert clean[0][1] == 200, "Reader should have completed all iterations"
            # Some writers may have lost (duplicate with different IDs is impossible,
            # so all 6 should succeed)
            assert len([r for r in results if r[0] == "ok"]) == 6, f"Expected 6 OK, got {results}"

    def test_no_partial_pointer_during_concurrent_updates(self):
        """A1/A5: Concurrent updates must never leave a partial / dangling
        record reference. Every plugin ID in the registry must resolve to a
        complete record with all required fields at all times.
        """
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            def _writer(registry_path: str, plugin_id: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
                registry = PersistentPluginRegistry(Path(registry_path))
                record = PluginRegistryRecord(
                    plugin_id=plugin_id,
                    version="1.0.0",
                    installation_id=f"inst-{plugin_id}",
                    manifest_digest="sha256:aaa",
                    bundle_digest="sha256:bbb",
                    signature_trust="trusted",
                    requested_capabilities=[],
                    granted_capabilities=[],
                    configuration_digest="sha256:ccc",
                    state="installed",
                    install_timestamp="2026-01-01T00:00:00Z",
                    publisher=None,
                    sdk_compatibility="1.0",
                    quarantine_state=None,
                )
                try:
                    registry.register(record)
                    # Immediately flip state to exercise read-during-write
                    registry.set_state(plugin_id, "active")
                    q.put(("ok", plugin_id))
                except Exception as e:
                    q.put(("error", plugin_id, str(e)))

            def _reader(registry_path: str, iterations: int, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry
                import time
                p = Path(registry_path)
                registry = PersistentPluginRegistry(p)
                for _ in range(iterations):
                    for plugin_id in [f"plugin-{i}" for i in range(6)]:
                        rec = registry.get(plugin_id)
                        if rec is not None:
                            # Every returned record must be complete
                            assert rec.plugin_id == plugin_id, f"ID mismatch: {rec.plugin_id} != {plugin_id}"
                            assert rec.version is not None
                            assert rec.installation_id is not None
                            assert rec.manifest_digest is not None
                            assert rec.bundle_digest is not None
                            assert rec.signature_trust is not None
                            assert rec.state in {"installed", "active", "disabled"}
                            assert rec.install_timestamp is not None
                            assert rec.sdk_compatibility is not None
                    time.sleep(0.01)
                q.put(("clean", iterations))

            writers = []
            for i in range(6):
                p = multiprocessing.Process(
                    target=_writer, args=(str(registry_path), f"plugin-{i}", q)
                )
                writers.append(p)

            reader = multiprocessing.Process(
                target=_reader, args=(str(registry_path), 100, q)
            )

            reader.start()
            for w in writers:
                w.start()
            for w in writers:
                w.join(timeout=15)
            reader.join(timeout=5)

            assert not reader.is_alive(), "Reader timed out"

            results = []
            while not q.empty():
                results.append(q.get_nowait())

            errors = [r for r in results if r[0] == "error"]
            torn = [r for r in results if r[0] == "torn"]
            clean = [r for r in results if r[0] == "clean"]

            assert len(torn) == 0, f"Partial pointer detected: {torn}"
            assert len(errors) == 0, f"Unexpected writer errors: {errors}"
            assert len(clean) == 1 and clean[0][1] == 100

    def test_registry_state_remains_valid_after_race(self):
        """A1/A5: After a concurrent register race, the registry file must remain
        fully valid — schema intact, reloadable, no partial writes or corruption."""
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            def _worker(registry_path: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord
                registry = PersistentPluginRegistry(Path(registry_path))
                record = PluginRegistryRecord(
                    plugin_id="plugin-y",
                    version="2.0.0",
                    installation_id="inst-y",
                    manifest_digest="sha256:aaa",
                    bundle_digest="sha256:bbb",
                    signature_trust="trusted",
                    requested_capabilities=[],
                    granted_capabilities=[],
                    configuration_digest="sha256:ccc",
                    state="installed",
                    install_timestamp="2026-01-01T00:00:00Z",
                    publisher=None,
                    sdk_compatibility="1.0",
                    quarantine_state=None,
                )
                try:
                    registry.register(record)
                    q.put(("ok", None))
                except Exception as e:
                    q.put(("error", str(e)))

            # Pre-populate
            registry = PersistentPluginRegistry(registry_path)
            existing = PluginRegistryRecord(
                plugin_id="plugin-y",
                version="1.0.0",
                installation_id="inst-y-old",
                manifest_digest="sha256:old",
                bundle_digest="sha256:old",
                signature_trust="trusted",
                requested_capabilities=[],
                granted_capabilities=[],
                configuration_digest="sha256:old",
                state="installed",
                install_timestamp="2026-01-01T00:00:00Z",
                publisher=None,
                sdk_compatibility="1.0",
                quarantine_state=None,
            )
            registry.register(existing)

            p = multiprocessing.Process(target=_worker, args=(str(registry_path), q))
            p.start()
            p.join(timeout=10)
            assert not p.is_alive()

            # Regardless of winner/loser, the file must be fully valid
            reloaded = PersistentPluginRegistry(registry_path)
            assert reloaded._data.get("schema_version") == 1
            plugins = reloaded._data.get("plugins", {})
            assert "plugin-y" in plugins
            record = reloaded.get("plugin-y")
            assert record is not None
            assert record.plugin_id == "plugin-y"
            assert record.version == "1.0.0"  # original winner's version
            assert record.state == "installed"
            # All fields present (no partial corruption)
            assert record.installation_id == "inst-y-old"
            assert record.manifest_digest == "sha256:old"
            assert record.bundle_digest == "sha256:old"
            assert record.signature_trust == "trusted"
            assert record.requested_capabilities == []
            assert record.granted_capabilities == []
            assert record.configuration_digest == "sha256:old"
            assert record.publisher is None
            assert record.sdk_compatibility == "1.0"
            assert record.quarantine_state is None

    def test_registry_set_state_concurrently(self):
        """A5: Two processes call set_state() on the same plugin simultaneously.

        Both load the registry, modify the state field in their own memory,
        then replace the file. Last write wins; one state change may be lost.
        No crash, file remains valid.
        """
        from release_engine.plugin_registry import PersistentPluginRegistry, PluginRegistryRecord

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            registry = PersistentPluginRegistry(registry_path)
            record = PluginRegistryRecord(
                plugin_id="plugin-x",
                version="1.0.0",
                installation_id="inst-x",
                manifest_digest="sha256:aaa",
                bundle_digest="sha256:bbb",
                signature_trust="trusted",
                requested_capabilities=[],
                granted_capabilities=[],
                configuration_digest="sha256:ccc",
                state="installed",
                install_timestamp="2026-01-01T00:00:00Z",
                publisher=None,
                sdk_compatibility="1.0",
                quarantine_state=None,
            )
            registry.register(record)

            q = multiprocessing.Queue()

            def _worker_set_state(registry_path: str, state: str, q):
                from pathlib import Path
                from release_engine.plugin_registry import PersistentPluginRegistry
                registry = PersistentPluginRegistry(Path(registry_path))
                try:
                    registry.set_state("plugin-x", state)
                    q.put(("set", state))
                except Exception as e:
                    q.put(("error", state, str(e)))

            p1 = multiprocessing.Process(
                target=_worker_set_state, args=(str(registry_path), "active", q)
            )
            p2 = multiprocessing.Process(
                target=_worker_set_state, args=(str(registry_path), "disabled", q)
            )
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            set_events = [e for e in events if e[0] == "set"]
            errors = [e for e in events if e[0] == "error"]

            for err in errors:
                pytest.fail(f"Unexpected error: {err}")

            assert len(set_events) == 2, f"Expected 2 set_state calls, got {set_events}"

            # File valid
            import json
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            final_state = data["plugins"]["plugin-x"]["state"]
            # Final state is one of the two values (last write wins)
            assert final_state in {"active", "disabled"}, (
                f"Unexpected final state: {final_state}"
            )