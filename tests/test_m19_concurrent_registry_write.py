"""Tests for concurrent registry writes — documents last-write-wins behavior.

Refactored to use module-level worker functions so the suite runs under
Windows spawn as well as POSIX fork.
"""

from __future__ import annotations

import json
import multiprocessing
import tempfile
from pathlib import Path

import pytest

from release_engine.plugin_registry import (
    PersistentPluginRegistry,
    PluginRegistryRecord,
    RegistryError,
)


def _make_record(plugin_id: str, version: str, installation_id: str | None = None) -> PluginRegistryRecord:
    return PluginRegistryRecord(
        plugin_id=plugin_id,
        version=version,
        installation_id=installation_id or f"inst-{plugin_id}",
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


def _worker_write(registry_path: str, plugin_id: str, version: str, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    record = _make_record(plugin_id, version)
    try:
        registry.register(record)
        q.put(("registered", plugin_id))
    except Exception as e:
        q.put(("error", plugin_id, str(e)))


def _worker_register_preexisting(registry_path: str, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    record = _make_record("plugin-z", "1.0.0")
    try:
        registry.register(record)
        q.put(("ok", None))
    except RegistryError as e:
        q.put(("registry_error", str(e)))
    except Exception as e:
        q.put(("unexpected", type(e).__name__, str(e)))


def _worker_write_distinct(registry_path: str, plugin_id: str, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    record = _make_record(plugin_id, "1.0.0")
    try:
        registry.register(record)
        q.put(("ok", plugin_id))
    except Exception as e:
        q.put(("error", plugin_id, str(e)))


def _worker_reader(registry_path: str, iterations: int, q) -> None:
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
    q.put(("clean", iterations))


def _worker_write_and_activate(registry_path: str, plugin_id: str, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    record = _make_record(plugin_id, "1.0.0")
    try:
        registry.register(record)
        registry.set_state(plugin_id, "active")
        q.put(("ok", plugin_id))
    except Exception as e:
        q.put(("error", plugin_id, str(e)))


def _worker_reader_complete(registry_path: str, iterations: int, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    for _ in range(iterations):
        for plugin_id in [f"plugin-{i}" for i in range(6)]:
            rec = registry.get(plugin_id)
            if rec is not None:
                assert rec.plugin_id == plugin_id
                assert rec.version is not None
                assert rec.installation_id is not None
                assert rec.manifest_digest is not None
                assert rec.bundle_digest is not None
                assert rec.signature_trust is not None
                assert rec.state in {"installed", "active", "disabled"}
                assert rec.install_timestamp is not None
                assert rec.sdk_compatibility is not None
    q.put(("clean", iterations))


def _worker_set_state(registry_path: str, state: str, q) -> None:
    registry = PersistentPluginRegistry(Path(registry_path))
    try:
        registry.set_state("plugin-x", state)
        q.put(("set", state))
    except Exception as e:
        q.put(("error", state, str(e)))


class TestConcurrentRegistryWrites:
    def test_two_registry_writers_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()
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

            assert len(registered) == 1
            assert len(errors) == 1
            assert "already registered" in errors[0][2]

            assert registry_path.exists()
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            assert "plugins" in data
            assert data["plugins"]["plugin-a"]["version"] in {"1.0.0", "2.0.0"}

    def test_registry_register_loser_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            registry = PersistentPluginRegistry(registry_path)
            existing = _make_record("plugin-z", "0.9.0", installation_id="inst-z-old")
            registry.register(existing)

            p = multiprocessing.Process(target=_worker_register_preexisting, args=(str(registry_path), q))
            p.start()
            p.join(timeout=10)
            assert not p.is_alive()

            ev = q.get(timeout=5)
            assert ev[0] == "registry_error"
            assert "already registered" in ev[1].lower()

            data = json.loads(registry_path.read_text(encoding="utf-8"))
            assert data["plugins"]["plugin-z"]["version"] == "0.9.0"

    def test_no_torn_json_under_concurrent_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            writers = [
                multiprocessing.Process(target=_worker_write_distinct, args=(str(registry_path), f"plugin-{i}", q))
                for i in range(6)
            ]
            reader = multiprocessing.Process(target=_worker_reader, args=(str(registry_path), 200, q))

            reader.start()
            for w in writers:
                w.start()
            for w in writers:
                w.join(timeout=15)
            reader.join(timeout=5)

            assert not reader.is_alive()

            results = []
            while not q.empty():
                results.append(q.get_nowait())

            torn = [r for r in results if r[0] == "torn"]
            clean = [r for r in results if r[0] == "clean"]

            assert len(torn) == 0, f"Torn JSON detected: {torn}"
            assert len(clean) == 1
            assert clean[0][1] == 200
            assert len([r for r in results if r[0] == "ok"]) == 6

    def test_no_partial_pointer_during_concurrent_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            writers = [
                multiprocessing.Process(target=_worker_write_and_activate, args=(str(registry_path), f"plugin-{i}", q))
                for i in range(6)
            ]
            reader = multiprocessing.Process(target=_worker_reader_complete, args=(str(registry_path), 100, q))

            reader.start()
            for w in writers:
                w.start()
            for w in writers:
                w.join(timeout=15)
            reader.join(timeout=5)

            assert not reader.is_alive()

            results = []
            while not q.empty():
                results.append(q.get_nowait())

            errors = [r for r in results if r[0] == "error"]
            torn = [r for r in results if r[0] == "torn"]
            clean = [r for r in results if r[0] == "clean"]

            assert len(torn) == 0
            assert len(errors) == 0
            assert len(clean) == 1 and clean[0][1] == 100

    def test_registry_state_remains_valid_after_race(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            q = multiprocessing.Queue()

            registry = PersistentPluginRegistry(registry_path)
            existing = _make_record("plugin-y", "1.0.0", installation_id="inst-y-old")
            registry.register(existing)

            p = multiprocessing.Process(target=_worker_write_distinct, args=(str(registry_path), "plugin-y", q))
            p.start()
            p.join(timeout=10)
            assert not p.is_alive()

            reloaded = PersistentPluginRegistry(registry_path)
            assert reloaded._data.get("schema_version") == 1
            plugins = reloaded._data.get("plugins", {})
            assert "plugin-y" in plugins
            record = reloaded.get("plugin-y")
            assert record is not None
            assert record.plugin_id == "plugin-y"
            assert record.version == "1.0.0"
            assert record.state == "installed"
            assert record.installation_id == "inst-y-old"

    def test_registry_set_state_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            registry = PersistentPluginRegistry(registry_path)
            registry.register(_make_record("plugin-x", "1.0.0"))

            q = multiprocessing.Queue()
            p1 = multiprocessing.Process(target=_worker_set_state, args=(str(registry_path), "active", q))
            p2 = multiprocessing.Process(target=_worker_set_state, args=(str(registry_path), "disabled", q))
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

            assert len(set_events) == 2

            data = json.loads(registry_path.read_text(encoding="utf-8"))
            final_state = data["plugins"]["plugin-x"]["state"]
            assert final_state in {"active", "disabled"}
