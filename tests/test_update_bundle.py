"""Tests for bundle extraction safety."""

from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from updates.bundle import extract_bundle
from updates.errors import BundleError


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bundle = self.tmp / "bundle.tar.gz"
        self.dest = self.tmp / "dest"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_bundle(self, members):
        with tarfile.open(self.bundle, "w:gz") as tar:
            for arcname, content in members:
                import os
                info = tarfile.TarInfo(name=arcname)
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))

    def test_traversal_rejected(self):
        self._make_bundle([("../evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_absolute_path_rejected(self):
        self._make_bundle([("/etc/evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_symlink_rejected(self):
        with tarfile.open(self.bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_valid_bundle_extracts(self):
        self._make_bundle([("bin/hive", b"hive"), ("lib/core.py", b"pass")])
        extract_bundle(self.bundle, self.dest)
        self.assertTrue((self.dest / "bin" / "hive").exists())


    def test_windows_drive_path_rejected(self):
        self._make_bundle([("C:/evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_unc_path_rejected(self):
        self._make_bundle([("//server/share/evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_backslash_separator_rejected(self):
        self._make_bundle([("dir\\evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_nested_traversal_rejected(self):
        self._make_bundle([("foo/bar/../../evil.txt", b"bad")])
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_hardlink_rejected(self):
        with tarfile.open(self.bundle, "w:gz") as tar:
            info = tarfile.TarInfo(name="hardlink")
            info.type = tarfile.LNKTYPE
            info.linkname = "/etc/passwd"
            info.size = 0
            tar.addfile(info)
        with self.assertRaises(BundleError):
            extract_bundle(self.bundle, self.dest)

    def test_zip_traversal_rejected(self):
        import zipfile
        zip_path = self.tmp / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("../evil.txt", b"bad")
        with self.assertRaises(BundleError):
            extract_bundle(zip_path, self.dest)


if __name__ == "__main__":
    unittest.main()
