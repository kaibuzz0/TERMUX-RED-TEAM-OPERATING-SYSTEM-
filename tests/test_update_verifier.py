"""Tests for bundle verification orchestrator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from updates import generate_keypair, sign_metadata, build_metadata, TrustStore, BundleVerifier
from updates.manifest import build_manifest
from updates.bundle import create_tar_bundle


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        self.src.mkdir()
        (self.src / "bin").mkdir()
        (self.src / "bin" / "hive").write_text("hive", encoding="utf-8")
        self.private, self.public = generate_keypair()
        manifest = build_manifest(self.src, self.src)
        artifacts = [
            {"name": e["path"], "size": e["size"], "sha256": e["sha256"]}
            for e in manifest
        ]
        meta = build_metadata("1.0.0", "rel-1", "abc", artifacts, ["termux"], ["aarch64"], "0.1.0", security_sequence=2)
        signed = sign_metadata(meta, self.private, "key1")
        self.bundle = self.tmp / "bundle.tar.gz"
        create_tar_bundle(self.src, self.bundle, manifest, signed)

        self.trust = TrustStore()
        from updates.signing import export_public_key_pem
        self.trust.add_key("key1", export_public_key_pem(self.public, "key1"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_verified_bundle(self):
        verifier = BundleVerifier(self.trust, "termux", "aarch64", current_sequence=1)
        work = self.tmp / "work"
        result = verifier.verify(self.bundle, work)
        self.assertTrue(result["verified"])
        self.assertEqual(result["metadata"]["release"]["release_id"], "rel-1")

    def test_anti_rollback(self):
        verifier = BundleVerifier(self.trust, "termux", "aarch64", current_sequence=5)
        work = self.tmp / "work"
        with self.assertRaises(Exception):
            verifier.verify(self.bundle, work)

    def test_revoked(self):
        verifier = BundleVerifier(self.trust, "termux", "aarch64", current_sequence=1)
        verifier.add_revoked_sequence(2)
        work = self.tmp / "work"
        with self.assertRaises(Exception):
            verifier.verify(self.bundle, work)


if __name__ == "__main__":
    unittest.main()
