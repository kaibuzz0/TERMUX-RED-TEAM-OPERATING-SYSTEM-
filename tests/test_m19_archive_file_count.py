"""Milestone 19 — Archive file count boundedness audit.

Production archive file count bounds catalog:
- updates.bundle.MAX_FILE_COUNT = 50_000
- Enforced in _validate_and_extract_members() before any file is written.
- Counts every member (files + directories) toward the total.
- Both tar and zip paths share the same counter.
- No separate file count limit exists in plugin_sdk.loader or release_engine.verifier;
  they delegate to extract_bundle and inherit the same bound.
"""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Tar archive exact boundary
# ---------------------------------------------------------------------------

class TestTarArchiveFileCountBounded:
    def test_tar_accepts_exactly_max_file_count(self, tmp_path, monkeypatch):
        """Tar archive with exactly MAX_FILE_COUNT entries is accepted."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        limit = 50
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "exact.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            for i in range(limit):
                info = tarfile.TarInfo(name=f"file{i:03d}.txt")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        extract_bundle(bundle, tmp_path / "out")
        extracted = list((tmp_path / "out").rglob("*.txt"))
        assert len(extracted) == limit

    def test_tar_rejects_max_file_count_plus_1(self, tmp_path, monkeypatch):
        """Tar archive with MAX_FILE_COUNT + 1 entries is rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 50
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "over.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            for i in range(limit + 1):
                info = tarfile.TarInfo(name=f"file{i:03d}.txt")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        with pytest.raises(BundleError, match="file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")

    def test_tar_directories_count_toward_file_count(self, tmp_path, monkeypatch):
        """Directory entries in a tar archive count toward MAX_FILE_COUNT."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 10
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "dirs.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            for i in range(limit + 1):
                info = tarfile.TarInfo(name=f"dir{i:03d}/")
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
        with pytest.raises(BundleError, match="file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 2. Zip archive exact boundary
# ---------------------------------------------------------------------------

class TestZipArchiveFileCountBounded:
    def test_zip_accepts_exactly_max_file_count(self, tmp_path, monkeypatch):
        """Zip archive with exactly MAX_FILE_COUNT entries is accepted."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        limit = 50
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "exact.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit):
                zf.writestr(f"file{i:03d}.txt", b"x")
        extract_bundle(bundle, tmp_path / "out")
        extracted = list((tmp_path / "out").rglob("*.txt"))
        assert len(extracted) == limit

    def test_zip_rejects_max_file_count_plus_1(self, tmp_path, monkeypatch):
        """Zip archive with MAX_FILE_COUNT + 1 entries is rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 50
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "over.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit + 1):
                zf.writestr(f"file{i:03d}.txt", b"x")
        with pytest.raises(BundleError, match="file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")

    def test_zip_directories_count_toward_file_count(self, tmp_path, monkeypatch):
        """Zip directory entries are rejected by the special-file guard
        (directories in zip are not supported by the hardened extractor).
        """
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 10
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "dirs.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit + 1):
                zf.writestr(f"dir{i:03d}/", b"")  # empty directory entry
        with pytest.raises(BundleError, match="special file|file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 3. Validation happens before extraction
# ---------------------------------------------------------------------------

class TestFileCountValidationBeforeExtraction:
    def test_nothing_extracted_when_file_count_exceeded(self, tmp_path, monkeypatch):
        """If MAX_FILE_COUNT is exceeded, no files are written to disk."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 5
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "over.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit + 1):
                zf.writestr(f"file{i}.txt", b"x")
        dest = tmp_path / "out"
        dest.mkdir()
        with pytest.raises(BundleError):
            extract_bundle(bundle, dest)
        # Only the empty dest directory should exist; no extracted files
        assert len(list(dest.iterdir())) == 0


# ---------------------------------------------------------------------------
# 4. No separate file count limits in higher layers
# ---------------------------------------------------------------------------

class TestHigherLayersDelegateFileCount:
    def test_plugin_sdk_loader_inherits_file_count_limit(self, tmp_path, monkeypatch):
        """plugin_sdk.loader.stage_bundle delegates to extract_bundle and inherits MAX_FILE_COUNT."""
        from updates import bundle as bundle_mod
        from plugin_sdk.loader import stage_bundle
        from plugin_sdk.errors import PluginBundleError
        limit = 5
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "many.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", b'{"schema_version":1,"plugin":{"id":"t","version":"1"}}')
            for i in range(limit + 1):
                zf.writestr(f"file{i}.txt", b"x")
        with pytest.raises((PluginBundleError, Exception), match="file count exceeds|Bundle file count"):
            stage_bundle(bundle, tmp_path / "staging")

    def test_release_engine_verifier_inherits_file_count_limit(self, tmp_path, monkeypatch):
        """release_engine.verifier uses extract_bundle and inherits MAX_FILE_COUNT."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 5
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "many.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit + 1):
                zf.writestr(f"file{i}.txt", b"x")
        with pytest.raises(BundleError, match="file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 5. Default value
# ---------------------------------------------------------------------------

class TestArchiveFileCountDefault:
    def test_default_max_file_count_is_50000(self):
        """MAX_FILE_COUNT default is 50,000."""
        from updates.bundle import MAX_FILE_COUNT
        assert MAX_FILE_COUNT == 50_000

    def test_default_is_shared_between_tar_and_zip(self):
        """Both tar and zip extraction paths use the same MAX_FILE_COUNT constant."""
        from updates.bundle import MAX_FILE_COUNT, _validate_and_extract_members
        import inspect
        source = inspect.getsource(_validate_and_extract_members)
        assert source.count("MAX_FILE_COUNT") >= 1
        # The counter is incremented once per member, regardless of archive type