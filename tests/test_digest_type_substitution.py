"""Verify digest cannot be substituted between object types.

Different object types produce different canonical inputs to SHA-256,
making cross-type digest substitution infeasible. This test validates
that verification binds each digest to its intended object type.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from release_engine.manifest import manifest_digest
from release_engine.reproducibility import compute_bundle_digest
from release_engine.signing import sign_release_metadata
from release_engine.verifier import verify_release_bundle
from release_engine.errors import ReleaseFormatError
from updates.manifest import _sha256
from updates.signing import export_public_key_pem
from updates.trust import TrustStore
from updates.bundle import create_tar_bundle, extract_bundle


class TestDigestTypeSubstitution:
    """Digest substitution between object types must fail verification."""

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

    def _build_bundle(self, tmp: str, manifest: list, metadata: dict, priv: Ed25519PrivateKey, custom_manifest_digest: str | None = None, source_name: str = "source"):
        """Build a valid bundle with given manifest and metadata."""
        source = Path(tmp) / source_name
        source.mkdir()
        for entry in manifest:
            if entry.get("path"):
                f = source / entry["path"]
                f.parent.mkdir(parents=True, exist_ok=True)
                content = entry.get("content", "x")
                f.write_text(content, encoding="utf-8")
                entry["sha256"] = __import__("hashlib").sha256(content.encode("utf-8")).hexdigest()
                entry["size"] = f.stat().st_size
                if "content" in entry:
                    del entry["content"]

        digest = custom_manifest_digest if custom_manifest_digest is not None else manifest_digest(manifest)
        metadata = dict(metadata)
        metadata["manifest_digest"] = digest
        signed = sign_release_metadata(metadata, priv, "test-key", digest)

        bundle = Path(tmp) / "bundle.tar.gz"
        create_tar_bundle(source, bundle, manifest, signed)
        return bundle

    # -----------------------------------------------------------------------
    # 1. Manifest digest vs per-file sha256 substitution
    # -----------------------------------------------------------------------

    def test_manifest_digest_cannot_use_file_sha256(self):
        """A per-file sha256 must not be accepted as a manifest digest."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            # Build a bundle where manifest_digest is a per-file sha256 (wrong type)
            manifest = [{"path": "a.py", "content": "print(1)"}]
            # Compute per-file sha256 (wrong type for manifest digest)
            file_sha = __import__("hashlib").sha256("print(1)".encode("utf-8")).hexdigest()
            bundle = self._build_bundle(tmp, manifest, self._make_metadata(), priv, custom_manifest_digest=file_sha)

            # Verification must fail — per-file sha256 != manifest digest
            verify_work = Path(tmp) / "verify"
            with pytest.raises(ReleaseFormatError, match="manifest digest mismatch"):
                verify_release_bundle(bundle, verify_work, store)

    # -----------------------------------------------------------------------
    # 2. Manifest digest vs raw bundle digest substitution
    # -----------------------------------------------------------------------

    def test_manifest_digest_cannot_use_bundle_digest(self):
        """A raw bundle file digest must not be accepted as a manifest digest."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            # First compute a bundle digest (wrong type)
            manifest = [{"path": "a.py", "content": "print(1)"}]
            bundle = self._build_bundle(tmp, manifest, self._make_metadata(), priv, source_name="source1")
            bundle_digest = compute_bundle_digest(bundle)

            # Now build a NEW bundle with the bundle_digest substituted as manifest_digest
            manifest2 = [{"path": "a.py", "content": "print(1)"}]
            bundle2 = self._build_bundle(tmp, manifest2, self._make_metadata(), priv, custom_manifest_digest=bundle_digest, source_name="source2")

            # Verification must fail
            verify_work = Path(tmp) / "verify"
            with pytest.raises(ReleaseFormatError, match="manifest digest mismatch"):
                verify_release_bundle(bundle2, verify_work, store)

    # -----------------------------------------------------------------------
    # 3. Different manifest produces different digest (same logical content, different format)
    # -----------------------------------------------------------------------

    def test_different_manifest_formats_produce_different_digests(self):
        """Manifest entries with extra/missing fields must produce different canonical digests."""
        m1 = [{"path": "a.py", "hash": "abc"}]
        m2 = [{"path": "a.py", "hash": "abc", "extra": "x"}]
        m3 = [{"path": "a.py", "hash": "abc", "size": 1}]

        d1 = manifest_digest(m1)
        d2 = manifest_digest(m2)
        d3 = manifest_digest(m3)

        # All should be different — the canonical JSON includes all fields
        assert d1 != d2
        assert d1 != d3
        assert d2 != d3

    # -----------------------------------------------------------------------
    # 4. Verify that different object types have different canonical forms
    # -----------------------------------------------------------------------

    def test_canonical_forms_are_type_distinct(self):
        """Manifest JSON, raw file bytes, and bundle bytes must have different canonical forms."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.py"
            content = 'print("hello")'
            f.write_text(content, encoding="utf-8")

            # Type 1: manifest digest (canonical JSON of list-of-dicts)
            manifest = [{"path": "test.py", "hash": "abc"}]
            d_manifest = manifest_digest(manifest)

            # Type 2: raw file sha256 (file bytes)
            d_file = _sha256(f)

            # Type 3: bundle digest (also file bytes, but different file)
            bundle = Path(tmp) / "bundle.tar.gz"
            import tarfile
            with tarfile.open(bundle, "w:gz") as tar:
                tar.add(f, arcname="test.py")
            d_bundle = compute_bundle_digest(bundle)

            # All three must differ — different canonical inputs
            assert d_manifest != d_file, "Manifest digest collided with file sha256"
            assert d_manifest != d_bundle, "Manifest digest collided with bundle digest"
            assert d_file != d_bundle, "File sha256 collided with bundle digest"

    # -----------------------------------------------------------------------
    # 5. Type confusion: manifest with only sha256 field (looks like a file digest)
    # -----------------------------------------------------------------------

    def test_manifest_with_sha256_field_is_still_manifest_digest(self):
        """Even if manifest entries contain sha256 values, the manifest digest is of the entries, not the files."""
        import hashlib
        content = "hello"
        file_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Manifest entry containing a sha256 string
        manifest = [{"path": "x.py", "hash": "abc", "size": 5, "sha256": file_sha}]
        d_manifest = manifest_digest(manifest)

        # The file sha256 itself
        d_file = file_sha

        # These must differ — manifest digest includes path, hash, size, sha256 fields
        assert d_manifest != d_file
        assert len(d_manifest) == 64
        assert len(d_file) == 64
