"""Milestone 19 — JSON document size boundedness audit.

Tests every production JSON loading point for size enforcement.
Only `config_engine.loader.load_json_file()` enforces a bound (5 MB).
All other loaders are unbounded — documented as accepted debt.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. config_engine.loader.load_json_file — BOUNDED at 5 MB
# ---------------------------------------------------------------------------

class TestConfigLoaderJsonSizeBounded:
    def test_load_json_file_accepts_exactly_limit(self):
        """load_json_file accepts file whose byte size == synthetic limit exactly."""
        from config_engine.loader import load_json_file
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "exact.json"
            limit = 1024
            # Build payload with exact byte length via json.dumps
            for guess in range(limit - 30, limit + 1):
                raw = json.dumps({"d": "x" * guess})
                if len(raw.encode("utf-8")) == limit:
                    p.write_text(raw, encoding="utf-8")
                    break
            assert p.stat().st_size == limit
            data = load_json_file(p, max_size_bytes=limit)
            assert "d" in data

    def test_load_json_file_rejects_limit_plus_1(self):
        """load_json_file rejects file whose byte size == synthetic limit + 1."""
        from config_engine.loader import load_json_file
        from config_engine.errors import ConfigValidationError
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "over.json"
            limit = 1024
            target = limit + 1
            for guess in range(target - 30, target + 1):
                raw = json.dumps({"d": "x" * guess})
                if len(raw.encode("utf-8")) == target:
                    p.write_text(raw, encoding="utf-8")
                    break
            assert p.stat().st_size == target
            with pytest.raises(ConfigValidationError, match="too large"):
                load_json_file(p, max_size_bytes=limit)


# ---------------------------------------------------------------------------
# 2. hive_broker.cli._load_manifest — UNBOUNDED
# ---------------------------------------------------------------------------

class TestBrokerCliManifestUnbounded:
    def test_cli_load_manifest_has_no_size_limit(self):
        """hive_broker.cli._load_manifest parses arbitrarily large JSON
        without rejecting on size — accepted debt.
        """
        from hive_broker.cli import _load_manifest
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            padding = "x" * (6 * 1024 * 1024)
            p.write_text(f'{{"data": "{padding}"}}', encoding="utf-8")
            assert p.stat().st_size > 5 * 1024 * 1024
            data = _load_manifest(str(p))
            assert len(data["data"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 3. installer.activate — lock / active-pointer / release-metadata UNBOUNDED
# ---------------------------------------------------------------------------

class TestInstallerActivateJsonUnbounded:
    def test_read_lock_has_no_size_limit(self):
        """installer.activate._read_lock parses lock JSON with no size check."""
        from installer.activate import ActiveState
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            state_root = Path(tmp) / "state"
            data_root.mkdir()
            state_root.mkdir()
            lock_path = state_root / ".install-lock"
            padding = "x" * (6 * 1024 * 1024)
            lock_path.write_text(
                json.dumps({"transaction_id": "txn-1", "padding": padding}),
                encoding="utf-8",
            )
            active = ActiveState(data_root=data_root, state_root=state_root, transaction_id="txn-2")
            data = active._read_lock()
            assert data is not None
            assert len(data.get("padding", "")) == 6 * 1024 * 1024

    def test_active_pointer_has_no_size_limit(self):
        """installer.activate._active_pointer parses JSON with no size check."""
        from installer.activate import ActiveState
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            state_root = Path(tmp) / "state"
            data_root.mkdir()
            state_root.mkdir()
            pointer = data_root / "active.json"
            padding = "x" * (6 * 1024 * 1024)
            pointer.write_text(
                json.dumps({
                    "schema_version": 1,
                    "active_release_id": "r1",
                    "active_runtime": "test",
                    "padding": padding,
                }),
                encoding="utf-8",
            )
            active = ActiveState(data_root=data_root, state_root=state_root, transaction_id="txn-1")
            data = active._active_pointer()
            assert data is not None
            assert data.active_release_id == "r1"

    def test_read_release_metadata_has_no_size_limit(self):
        """installer.activate._read_release_metadata parses JSON with no size check."""
        from installer.activate import ActiveState
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            state_root = Path(tmp) / "state"
            data_root.mkdir()
            state_root.mkdir()
            rel_dir = data_root / "releases" / "r1"
            rel_dir.mkdir(parents=True)
            meta = rel_dir / ".release.json"
            padding = "x" * (6 * 1024 * 1024)
            meta.write_text(
                json.dumps({
                    "schema_version": 1,
                    "release_id": "r1",
                    "transaction_id": "txn-1",
                    "state": "staged",
                    "repository": "repo",
                    "commit": "abc",
                    "canonical_source": "src",
                    "created_at": "2026-01-01T00:00:00",
                    "padding": padding,
                }),
                encoding="utf-8",
            )
            active = ActiveState(data_root=data_root, state_root=state_root, transaction_id="txn-1")
            info = active._read_release_metadata("r1")
            assert info.release_id == "r1"


# ---------------------------------------------------------------------------
# 4. installer.journal — UNBOUNDED
# ---------------------------------------------------------------------------

class TestInstallerJournalUnbounded:
    def test_journal_read_has_no_size_limit(self):
        """installer.journal.read() parses each line without size check."""
        from installer.journal import InstallJournal
        with tempfile.TemporaryDirectory() as tmp:
            journal = InstallJournal(
                journal_dir=Path(tmp) / "j",
                transaction_id="txn-1",
            )
            padding = "x" * (6 * 1024 * 1024)
            journal.append("test", "test", {"padding": padding})
            records = journal.read()
            assert len(records) == 1
            assert len(records[0]["details"]["padding"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 5. installer.plan — canonical metadata UNBOUNDED
# ---------------------------------------------------------------------------

class TestInstallerPlanCanonicalUnbounded:
    def test_load_canonical_metadata_has_no_size_limit(self):
        """installer.plan._load_canonical_metadata parses JSON with no size check."""
        from installer.plan import _load_canonical_metadata
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            padding = "x" * (6 * 1024 * 1024)
            (root / "hive-canonical.json").write_text(
                json.dumps({"version": "1.0.0", "padding": padding}),
                encoding="utf-8",
            )
            data = _load_canonical_metadata(root)
            assert len(data["padding"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 6. release_engine.verifier — metadata / manifest UNBOUNDED
# ---------------------------------------------------------------------------

class TestReleaseEngineVerifierUnbounded:
    def test_extract_and_load_metadata_has_no_size_limit(self, tmp_path):
        """release_engine.verifier inspect_release loads metadata.json without size check."""
        from release_engine.verifier import inspect_release
        from updates.bundle import create_tar_bundle
        work = tmp_path / "work"
        work.mkdir()
        bundle = tmp_path / "bundle.tar.gz"
        padding = "x" * (6 * 1024 * 1024)
        meta = {"version": "1.0.0", "padding": padding}
        manifest = [{"path": "a.txt", "size": 1, "sha256": "a" * 64}]
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("x", encoding="utf-8")
        (src / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (src / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        create_tar_bundle(src, bundle, manifest, meta)
        result = inspect_release(bundle, work)
        assert len(result["metadata"]["padding"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 7. release_engine.plugin_registry — UNBOUNDED
# ---------------------------------------------------------------------------

class TestPluginRegistryUnbounded:
    def test_plugin_registry_load_has_no_size_limit(self):
        """PersistentPluginRegistry._load parses JSON with no size check."""
        from release_engine.plugin_registry import PersistentPluginRegistry
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"
            padding = "x" * (6 * 1024 * 1024)
            p.write_text(
                json.dumps({"schema_version": 1, "plugins": {}, "padding": padding}),
                encoding="utf-8",
            )
            reg = PersistentPluginRegistry(path=p)
            assert len(reg._data["padding"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 8. release_engine.registry — UNBOUNDED
# ---------------------------------------------------------------------------

class TestReleaseRegistryUnbounded:
    def test_release_registry_load_has_no_size_limit(self):
        """ReleaseRegistry._load parses JSON with no size check."""
        from release_engine.registry import ReleaseRegistry
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"
            padding = "x" * (6 * 1024 * 1024)
            p.write_text(
                json.dumps({"schema_version": 1, "releases": [], "padding": padding}),
                encoding="utf-8",
            )
            reg = ReleaseRegistry(path=p)
            assert len(reg._data["padding"]) == 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# 9. release_engine.plugin_package — UNBOUNDED
# ---------------------------------------------------------------------------

class TestPluginPackageMetadataUnbounded:
    def test_plugin_sdk_load_manifest_has_no_size_limit(self, tmp_path):
        """plugin_sdk.manifest.load_manifest parses JSON without size check."""
        from plugin_sdk.manifest import load_manifest
        from plugin_sdk.errors import PluginManifestError
        manifest_path = tmp_path / "manifest.json"
        padding = "x" * (6 * 1024 * 1024)
        manifest_path.write_text(
            json.dumps({
                "schema_version": 1,
                "plugin": {"id": "p1", "version": "1.0.0", "author_key_id": "k1"},
                "padding": padding,
            }),
            encoding="utf-8",
        )
        # plugin_sdk manifest rejects unknown top-level fields; we catch that
        with pytest.raises(PluginManifestError, match="unknown top-level fields"):
            load_manifest(manifest_path)

    def test_plugin_package_verify_reads_unbounded(self, tmp_path):
        """release_engine.plugin_package.verify_plugin_package reads manifest+metadata
        without size check — but requires valid Ed25519 signature.
        """
        from release_engine.plugin_package import verify_plugin_package
        import zipfile
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from updates.trust import TrustStore

        private_key = Ed25519PrivateKey.generate()
        key_id = "test-key"
        padding = "x" * (6 * 1024 * 1024)
        manifest = {"plugin": {"id": "p1", "version": "1.0.0", "author_key_id": key_id}, "padding": padding}
        from updates.signing import sign_metadata
        metadata = sign_metadata(
            {"schema_version": 1, "plugin": {"id": "p1", "version": "1.0.0", "author_key_id": key_id}},
            private_key,
            key_id,
        )
        metadata["padding"] = padding

        package = tmp_path / "test.hivepkg"
        with zipfile.ZipFile(package, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("metadata.json", json.dumps(metadata))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            pub_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
            f.write(pub_pem)
            f.flush()
            trust = TrustStore.from_pem_file(Path(f.name))

        # Plugin SDK manifest validation rejects unknown fields, so this will fail
        # at manifest validation, not JSON size. The test documents the unbounded JSON
        # parse that happens *before* the schema rejection.
        from plugin_sdk.errors import PluginManifestError
        with pytest.raises(PluginManifestError, match="unknown top-level fields"):
            verify_plugin_package(package, tmp_path / "work", trust)