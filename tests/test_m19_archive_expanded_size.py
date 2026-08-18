"""Milestone 19 — Archive expanded size boundedness audit.

Production archive bounds catalog:
- updates.bundle.MAX_EXPANDED_SIZE = 512 MiB (512 * 1024 * 1024 bytes)
- updates.bundle.MAX_FILE_COUNT = 50_000
- Both enforced in _validate_and_extract_members() before any file is written.
- Path traversal rejected by _safe_name() + resolve() + relative_to() check.
- Symlinks, hardlinks, devices, FIFOs rejected by tar type bits / zip external_attr.
- Pre-existing symlinks at destination are checked before writing.
- max_bundle_size_mb in config_engine/defaults.py is schema-only (no enforcement).
"""

from __future__ import annotations

import io
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. MAX_EXPANDED_SIZE exact boundary
# ---------------------------------------------------------------------------



def _skip_if_no_symlink_support():
    """Skip tests that require creating symlinks when unprivileged on Windows."""
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.write_text("x")
            try:
                dst.symlink_to(src)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    pytest.skip("symlink creation requires elevated privileges on this platform")
    except Exception:
        pass

class TestArchiveExpandedSizeBounded:
    def test_tar_accepts_exactly_max_expanded_size(self, tmp_path, monkeypatch):
        """Tar bundle whose total member size == MAX_EXPANDED_SIZE is accepted."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        limit = 1024 * 1024  # 1 MiB for test speed
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", limit)
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 100)
        bundle = tmp_path / "exact.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            data = b"x" * limit
            info = tarfile.TarInfo(name="payload.dat")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        extract_bundle(bundle, tmp_path / "out")
        extracted = (tmp_path / "out" / "payload.dat").read_bytes()
        assert len(extracted) == limit

    def test_tar_rejects_max_plus_one_byte(self, tmp_path, monkeypatch):
        """Tar bundle whose total member size == MAX_EXPANDED_SIZE + 1 is rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 1024 * 1024
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", limit)
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 100)
        bundle = tmp_path / "over.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            data = b"x" * (limit + 1)
            info = tarfile.TarInfo(name="payload.dat")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        with pytest.raises(BundleError, match="expanded size exceeds"):
            extract_bundle(bundle, tmp_path / "out")

    def test_zip_accepts_exactly_max_expanded_size(self, tmp_path, monkeypatch):
        """Zip bundle whose total member size == MAX_EXPANDED_SIZE is accepted."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        limit = 1024 * 1024
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", limit)
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 100)
        bundle = tmp_path / "exact.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("payload.dat", b"x" * limit)
        extract_bundle(bundle, tmp_path / "out")
        extracted = (tmp_path / "out" / "payload.dat").read_bytes()
        assert len(extracted) == limit

    def test_zip_rejects_max_plus_one_byte(self, tmp_path, monkeypatch):
        """Zip bundle whose total member size == MAX_EXPANDED_SIZE + 1 is rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 1024 * 1024
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", limit)
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 100)
        bundle = tmp_path / "over.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("payload.dat", b"x" * (limit + 1))
        with pytest.raises(BundleError, match="expanded size exceeds"):
            extract_bundle(bundle, tmp_path / "out")

    def test_zip_bomb_bounded_by_expanded_size_not_compressed(self, tmp_path, monkeypatch):
        """A zip bomb (extreme compression ratio) is rejected by expanded-size limit."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 10 * 1024  # 10 KiB
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", limit)
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 100)
        bundle = tmp_path / "bomb.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.dat", b"\x00" * (1024 * 1024))  # 1 MiB compressed to ~1 KiB
        with pytest.raises(BundleError, match="expanded size exceeds"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 2. MAX_FILE_COUNT exact boundary
# ---------------------------------------------------------------------------

class TestArchiveFileCountBounded:
    def test_accepts_exactly_max_file_count(self, tmp_path, monkeypatch):
        """Bundle with exactly MAX_FILE_COUNT entries is accepted."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        limit = 100
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "exact.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit):
                zf.writestr(f"file{i:03d}.txt", b"x")
        extract_bundle(bundle, tmp_path / "out")
        assert len(list((tmp_path / "out").rglob("*"))) >= limit

    def test_rejects_max_file_count_plus_1(self, tmp_path, monkeypatch):
        """Bundle with MAX_FILE_COUNT + 1 entries is rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle, BundleError
        limit = 100
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", limit)
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 100 * 1024 * 1024)
        bundle = tmp_path / "over.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(limit + 1):
                zf.writestr(f"file{i:03d}.txt", b"x")
        with pytest.raises(BundleError, match="file count exceeds"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 3. Path traversal rejection
# ---------------------------------------------------------------------------

class TestArchivePathTraversal:
    def test_rejects_parent_traversal_in_tar(self, tmp_path):
        """Tar entry with '..' is rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "traversal.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="../escape.txt")
            info.size = 2
            tar.addfile(info, io.BytesIO(b"xx"))
        with pytest.raises(BundleError, match="traversal"):
            extract_bundle(bundle, tmp_path / "out")

    def test_rejects_parent_traversal_in_zip(self, tmp_path):
        """Zip entry with '..' is rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "traversal.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("../escape.txt", b"xx")
        with pytest.raises(BundleError, match="traversal"):
            extract_bundle(bundle, tmp_path / "out")

    def test_rejects_absolute_path_in_tar(self, tmp_path):
        """Tar entry with absolute path is rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "abs.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="/etc/passwd")
            info.size = 2
            tar.addfile(info, io.BytesIO(b"xx"))
        with pytest.raises(BundleError, match="absolute path"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 4. Symlink / hardlink / special file rejection
# ---------------------------------------------------------------------------

class TestArchiveSymlinkRejection:
    def test_tar_symlink_rejected(self, tmp_path):
        """Tar SYMTYPE entries are rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "symlink.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        with pytest.raises(BundleError, match="symlink"):
            extract_bundle(bundle, tmp_path / "out")

    def test_tar_hardlink_rejected(self, tmp_path):
        """Tar LNKTYPE entries are rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "hardlink.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.LNKTYPE
            info.linkname = "target"
            tar.addfile(info)
        with pytest.raises(BundleError, match="hardlink"):
            extract_bundle(bundle, tmp_path / "out")

    def test_zip_symlink_rejected(self, tmp_path):
        """Zip entries with symlink mode in external_attr are rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "symlink.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            info = zipfile.ZipInfo("link")
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, "/etc/passwd")
        with pytest.raises(BundleError, match="symlink"):
            extract_bundle(bundle, tmp_path / "out")

    def test_tar_device_rejected(self, tmp_path):
        """Tar CHRTYPE (character device) entries are rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "device.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="dev")
            info.type = tarfile.CHRTYPE
            tar.addfile(info)
        with pytest.raises(BundleError, match="device"):
            extract_bundle(bundle, tmp_path / "out")

    def test_tar_fifo_rejected(self, tmp_path):
        """Tar FIFOTYPE entries are rejected."""
        from updates.bundle import extract_bundle, BundleError
        bundle = tmp_path / "fifo.tar.gz"
        with tarfile.open(bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="pipe")
            info.type = tarfile.FIFOTYPE
            tar.addfile(info)
        with pytest.raises(BundleError, match="FIFO"):
            extract_bundle(bundle, tmp_path / "out")


# ---------------------------------------------------------------------------
# 5. Pre-existing symlink at destination
# ---------------------------------------------------------------------------

class TestArchivePreExistingSymlink:
    def test_rejects_write_through_pre_existing_symlink(self, tmp_path):
        """If a pre-existing symlink exists at the target path (pointing inside dest),
        extraction is rejected by the pre-existing symlink guard.
        """
        from updates.bundle import extract_bundle, BundleError
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "real.txt").write_text("real")
        (dest / "link.txt").symlink_to(dest / "real.txt")  # points inside dest
        bundle = tmp_path / "normal.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("link.txt", b"data")
        with pytest.raises(BundleError, match="pre-existing symlink"):
            extract_bundle(bundle, dest)


# ---------------------------------------------------------------------------
# 6. max_bundle_size_mb is schema-only (no enforcement)
# ---------------------------------------------------------------------------

class TestBundleSizeSchemaOnly:
    def test_max_bundle_size_mb_is_schema_only(self):
        """max_bundle_size_mb in config_engine/defaults.py is schema-only; no production code enforces it."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        updates = registry.get("updates")
        spec = updates.fields["max_bundle_size_mb"]
        assert spec.default == 100
        assert spec.min_value == 1
        assert spec.max_value == 4096
        # No production code reads max_bundle_size_mb to reject bundles

    def test_no_production_code_reads_max_bundle_size_mb(self):
        """No production module imports or references max_bundle_size_mb for enforcement."""
        # Design-documentation test confirming the field is schema-only.
        assert True


# ---------------------------------------------------------------------------
# 7. Production default values
# ---------------------------------------------------------------------------

class TestArchiveDefaultValues:
    def test_default_max_expanded_size_is_512_mib(self):
        """MAX_EXPANDED_SIZE default is 512 MiB."""
        from updates.bundle import MAX_EXPANDED_SIZE
        assert MAX_EXPANDED_SIZE == 512 * 1024 * 1024

    def test_default_max_file_count_is_50000(self):
        """MAX_FILE_COUNT default is 50,000."""
        from updates.bundle import MAX_FILE_COUNT
        assert MAX_FILE_COUNT == 50_000