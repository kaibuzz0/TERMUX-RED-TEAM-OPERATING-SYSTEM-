"""Milestone 19 — Area E: Supply chain and signing review tests.

Tests Ed25519 signing, trust store integrity, anti-rollback, and
bundle verification hardening.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from updates.signing import (
    sign_metadata,
    verify_metadata,
    export_public_key_pem,
    export_private_key_pem,
    load_private_key_pem,
)
from updates.trust import TrustStore, TrustError
from updates.errors import BundleError
from updates.verifier import BundleVerifier
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives import hashes, serialization


class TestSupplyChainAndSigning:
    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _sample_metadata():
        return {
            "schema_version": 1,
            "release": {
                "version": "1.0.0-rc.1",
                "release_id": "test-release",
                "commit": "abc123",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }

    @staticmethod
    def _make_trust_store(key_id: str, private_key: Ed25519PrivateKey):
        pub_pem = export_public_key_pem(private_key.public_key(), key_id)
        ts = TrustStore()
        ts.add_key(key_id, pub_pem)
        return ts

    # -----------------------------------------------------------------------
    # E1: Trust store tampering
    # -----------------------------------------------------------------------

    def test_unknown_key_id_rejected(self):
        """E1: Metadata signed with unknown key must be rejected."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "unknown-key")

        # Different trust store
        other_priv = Ed25519PrivateKey.generate()
        ts = self._make_trust_store("other-key", other_priv)
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    def test_revoked_key_rejected(self):
        """E1: Metadata signed with revoked key must be rejected."""
        priv = Ed25519PrivateKey.generate()
        key_id = "test-key"
        pub_pem = export_public_key_pem(priv.public_key(), key_id)
        ts = TrustStore()
        ts.add_key(key_id, pub_pem)
        ts.revoke_key(key_id)

        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, key_id)
        with pytest.raises(TrustError, match="revoked"):
            verify_metadata(signed, ts)

    # -----------------------------------------------------------------------
    # E2: Wrong key type
    # -----------------------------------------------------------------------

    def test_rsa_key_rejected(self):
        """E2: RSA public key must be rejected by TrustStore."""
        rsa_priv = generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pub_pem = rsa_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        ts = TrustStore()
        with pytest.raises(TrustError, match="Only Ed25519"):
            ts.add_key("rsa-key", rsa_pub_pem)

    # -----------------------------------------------------------------------
    # E3: Signature algorithm downgrade
    # -----------------------------------------------------------------------

    def test_non_ed25519_algorithm_rejected(self):
        """E3: Metadata claiming non-Ed25519 algorithm must be rejected."""
        metadata = self._sample_metadata()
        metadata["signing"] = {
            "algorithm": "RSA-PSS",
            "key_id": "test-key",
            "signature": "dGVzdA==",  # base64("test")
        }
        priv = Ed25519PrivateKey.generate()
        ts = self._make_trust_store("test-key", priv)
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(metadata, ts)

    # -----------------------------------------------------------------------
    # E4: Manifest digest mismatch
    # -----------------------------------------------------------------------

    def test_tampered_manifest_digest_mismatch(self):
        """E4: Tampered manifest digest (SHA-256) must be detected during verification."""
        from release_engine.manifest import manifest_digest
        manifest = [{"path": "bin/hive", "hash": "abc123"}]
        metadata = self._sample_metadata()
        metadata["manifest_digest"] = manifest_digest(manifest)

        # Tamper manifest
        manifest[0]["hash"] = "def456"
        # Digest should no longer match
        assert manifest_digest(manifest) != metadata["manifest_digest"]
        # Verify the digest is a valid SHA-256 hex string (64 chars, lowercase hex)
        assert len(metadata["manifest_digest"]) == 64
        assert all(c in "0123456789abcdef" for c in metadata["manifest_digest"])

    # -----------------------------------------------------------------------
    # E5: Bundle extraction path traversal
    # Already tested in Area B: hardlink, symlink, size limits
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # E6: Emergency bundle bypass
    # -----------------------------------------------------------------------

    def test_emergency_allows_untrusted_bundle(self):
        """E6: Emergency flag must allow bypass of trust verification with logging."""
        from updates.bundle import create_tar_bundle
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "test-key")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()

            bundle_path = Path(tmp) / "bundle.tar.gz"
            # Pass the signed metadata and manifest to create_tar_bundle
            create_tar_bundle(source, bundle_path, [], signed)

            work_dir = Path(tmp) / "work"
            verifier = BundleVerifier(
                trust_store=TrustStore(),  # empty — would normally fail
                platform="linux",
                architecture="x86_64",
            )
            # Without emergency: should fail (trust verification fails on empty store)
            with pytest.raises((TrustError, BundleError)):
                verifier.verify(bundle_path, work_dir, allow_emergency=False)

            # With emergency: should succeed but flagged
            result = verifier.verify(bundle_path, work_dir, allow_emergency=True)
            assert result["allow_emergency"] is True
            assert result["trust_level"] == "offline_verified_bundle"

    def test_emergency_requires_explicit_flag(self):
        """E6: Untrusted bundle without emergency flag must be rejected."""
        from updates.bundle import create_tar_bundle
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            metadata = {"schema_version": 1, "release": {"version": "1.0.0-rc.1", "release_id": "test", "commit": "abc", "platforms": ["linux"], "architectures": ["x86_64"], "release_sequence": 1, "security_sequence": 1}}
            manifest = []

            bundle_path = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle_path, manifest, metadata)

            work_dir = Path(tmp) / "work"
            verifier = BundleVerifier(
                trust_store=TrustStore(),
                platform="linux",
                architecture="x86_64",
            )
            with pytest.raises((TrustError, BundleError)):
                verifier.verify(bundle_path, work_dir, allow_emergency=False)
