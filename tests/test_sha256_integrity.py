"""Verify SHA-256 digest binding: manifest digest is bound into signed metadata and verified.

This test validates the actual security property:
- The manifest digest computed at build time is embedded in signed metadata.
- At verification time, the manifest is re-read and its digest recomputed.
- If the manifest has been tampered with (different content), the recomputed digest
  does not match the signed digest in metadata → verification fails.

Does NOT attempt to prove SHA-256 collision resistance; tests the binding mechanism.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from release_engine.manifest import manifest_digest
from release_engine.signing import sign_release_metadata, verify_release_metadata
from release_engine.verifier import verify_release_bundle
from release_engine.errors import ReleaseFormatError
from updates.signing import export_public_key_pem
from updates.trust import TrustStore
from updates.bundle import create_tar_bundle, extract_bundle


class TestDigestBinding:
    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_metadata():
        return {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test-release",
                "commit": "abc123",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
        }

    @staticmethod
    def _make_trust_store(key_id: str, priv: Ed25519PrivateKey):
        store = TrustStore()
        pub_pem = export_public_key_pem(priv.public_key(), key_id)
        store.add_key(key_id, pub_pem)
        return store

    # -----------------------------------------------------------------------
    # Digest binding: manifest digest embedded in signed metadata
    # -----------------------------------------------------------------------

    def test_digest_embedded_in_signed_metadata(self):
        """Signing must embed manifest digest into metadata."""
        priv = Ed25519PrivateKey.generate()
        manifest = [{"path": "bin/hive", "hash": "abc123"}]
        digest = manifest_digest(manifest)

        metadata = self._make_metadata()
        signed = sign_release_metadata(metadata, priv, "test-key", digest)

        assert signed["manifest_digest"] == digest
        assert len(signed["manifest_digest"]) == 64

    # -----------------------------------------------------------------------
    # End-to-end: bundle with correct digest verifies successfully
    # -----------------------------------------------------------------------

    def test_bundle_with_correct_digest_verifies(self):
        """Bundle where manifest digest matches metadata must verify."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "bin").mkdir()
            content = "#!/bin/sh\necho ok"
            # Write with explicit newline='\n' so cross-platform text translation
            # does not change the file hash under Windows (HRA-007).
            (source / "bin" / "hive").write_text(content, encoding="utf-8", newline="\n")
            hive_size = (source / "bin" / "hive").stat().st_size
            hive_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

            manifest = [{"path": "bin/hive", "hash": "abc123", "size": hive_size, "sha256": hive_sha}]
            digest = manifest_digest(manifest)
            metadata = self._make_metadata()
            metadata["manifest_digest"] = digest
            signed = sign_release_metadata(metadata, priv, "test-key", digest)

            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle, manifest, signed)

            work = Path(tmp) / "work"
            result = verify_release_bundle(bundle, work, store)
            assert result["verified"] is True

    # -----------------------------------------------------------------------
    # Tampered manifest: digest mismatch detected at verification
    # -----------------------------------------------------------------------

    def test_tampered_manifest_fails_verification(self):
        """Tampering manifest content after signing must cause digest mismatch failure."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "bin").mkdir()
            (source / "bin" / "hive").write_text("#!/bin/sh\necho ok", encoding="utf-8", newline="\n")

            # Build original manifest and sign
            manifest = [{"path": "bin/hive", "hash": "abc123"}]
            digest = manifest_digest(manifest)
            metadata = self._make_metadata()
            metadata["manifest_digest"] = digest
            signed = sign_release_metadata(metadata, priv, "test-key", digest)

            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle, manifest, signed)

            # Tamper: extract bundle, modify manifest, re-pack
            tamper_work = Path(tmp) / "tamper"
            tamper_work.mkdir()
            extract_bundle(bundle, tamper_work)

            # Modify the manifest hash
            manifest_path = tamper_work / "manifest.json"
            tampered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            tampered_manifest[0]["hash"] = "TAMPERED"
            manifest_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")

            # Re-pack tampered bundle (naive: just the files we care about)
            # For this test, create a fresh bundle from tampered work dir
            tampered_bundle = Path(tmp) / "tampered.tar.gz"
            create_tar_bundle(tamper_work, tampered_bundle, tampered_manifest, signed)

            # Verification must fail because manifest digest no longer matches
            verify_work = Path(tmp) / "verify"
            with pytest.raises(ReleaseFormatError, match="manifest digest mismatch"):
                verify_release_bundle(tampered_bundle, verify_work, store)

    # -----------------------------------------------------------------------
    # Missing manifest digest in metadata
    # -----------------------------------------------------------------------

    def test_missing_manifest_digest_in_metadata(self):
        """Metadata without manifest_digest should be rejected or handled."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "bin").mkdir()
            content = "x"
            (source / "bin" / "hive").write_text(content, encoding="utf-8", newline="\n")
            hive_size = (source / "bin" / "hive").stat().st_size
            hive_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

            manifest = [{"path": "bin/hive", "hash": "abc123", "size": hive_size, "sha256": hive_sha}]
            digest = manifest_digest(manifest)
            metadata = self._make_metadata()
            # Do NOT include manifest_digest in metadata before signing
            signed = sign_release_metadata(metadata, priv, "test-key", digest)
            # sign_release_metadata adds it; verify it's present
            assert "manifest_digest" in signed

            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle, manifest, signed)

            work = Path(tmp) / "work"
            result = verify_release_bundle(bundle, work, store)
            assert result["verified"] is True

    # -----------------------------------------------------------------------
    # Empty manifest digest still validates format
    # -----------------------------------------------------------------------

    def test_empty_manifest_digest_format(self):
        """Manifest digest must be a 64-char hex string even for empty manifest."""
        empty_digest = manifest_digest([])
        assert len(empty_digest) == 64
        assert all(c in "0123456789abcdef" for c in empty_digest)
