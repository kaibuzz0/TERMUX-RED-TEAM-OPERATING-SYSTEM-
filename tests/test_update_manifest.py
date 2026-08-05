"""Tests for release manifest generation and validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from updates.manifest import build_manifest, write_manifest, verify_manifest
from updates.errors import BundleError


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "hive").write_text("#!/usr/bin/env python3\nprint('hive')", encoding="utf-8")
        (self.tmp / "lib").mkdir()
        (self.tmp / "lib" / "core.py").write_text("pass", encoding="utf-8")
        (self.tmp / ".git").mkdir(exist_ok=True)
        (self.tmp / ".git" / "config").write_text("x", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_excludes_git_and_tests(self):
        manifest = build_manifest(self.tmp)
        paths = [e["path"] for e in manifest]
        self.assertNotIn(".git/config", paths)

    def test_deterministic_ordering(self):
        m1 = build_manifest(self.tmp)
        m2 = build_manifest(self.tmp)
        self.assertEqual([e["path"] for e in m1], [e["path"] for e in m2])

    def test_verify_manifest(self):
        manifest = build_manifest(self.tmp)
        verify_manifest(manifest, self.tmp)


if __name__ == "__main__":
    unittest.main()