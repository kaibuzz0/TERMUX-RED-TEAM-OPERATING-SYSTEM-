"""E1-FAIL-CLOSED: Malformed trust store fails closed.

A trust store with no valid keys, corrupted content, wrong key types, or
missing file produces an empty in-memory store. Any verification attempt
on such a store raises TrustError — no keys are trusted by default.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives import serialization

from updates.trust import TrustStore, TrustError, TrustedKey
from updates.signing import export_public_key_pem, sign_metadata, verify_metadata


class TestMalformedTrustStoreFailsClosed:
    """Any malformed trust store results in zero trusted keys."""

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

    # ------------------------------------------------------------------
    # Empty / missing / unparseable store = empty keys dict
    # ------------------------------------------------------------------

    def test_missing_file_returns_empty_store(self):
        """Non-existent PEM file → empty store → any verify raises TrustError."""
        ts = TrustStore.from_pem_file(Path("/nonexistent/store.pem"))
        assert ts.keys == {}
        # Cannot verify anything on empty store
        with pytest.raises(TrustError, match="Unknown key ID"):
            ts.verify("any-key", b"msg", b"sig")

    def test_empty_file_returns_empty_store(self):
        """Empty PEM file → empty store → any verify raises TrustError."""
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "empty.pem"
            pem_path.write_text("")
            ts = TrustStore.from_pem_file(pem_path)
            assert ts.keys == {}
            with pytest.raises(TrustError, match="Unknown key ID"):
                ts.verify("any-key", b"msg", b"sig")

    def test_garbage_file_returns_empty_store(self):
        """File with random bytes → empty store → any verify raises TrustError."""
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "garbage.pem"
            pem_path.write_text("totally not a pem file\n12345\n\n\n")
            ts = TrustStore.from_pem_file(pem_path)
            assert ts.keys == {}
            with pytest.raises(TrustError, match="Unknown key ID"):
                ts.verify("any-key", b"msg", b"sig")

    # ------------------------------------------------------------------
    # Corrupted PEM = skip corrupted block, keep valid ones
    # ------------------------------------------------------------------

    def test_corrupted_valid_mix_skips_corrupted(self):
        """File with one valid and one corrupted PEM → only valid loaded."""
        priv = Ed25519PrivateKey.generate()
        valid_pem = export_public_key_pem(priv.public_key(), "valid-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "mixed.pem"
            pem_path.write_text(
                "-----BEGIN PUBLIC KEY-----\nINVALID\n-----END PUBLIC KEY-----\n"
                + valid_pem
            )
            ts = TrustStore.from_pem_file(pem_path)
            assert len(ts.keys) == 1
            assert "valid-key" in ts.keys
            # Corrupted key not present
            assert "key-1" not in ts.keys or ts.keys.get("key-1") is None

    # ------------------------------------------------------------------
    # Wrong key type = skip, store remains empty
    # ------------------------------------------------------------------

    def test_rsa_only_file_returns_empty_store(self):
        """File with only RSA keys → empty store (Ed25519 enforced)."""
        rsa_priv = generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "rsa_only.pem"
            pem_path.write_text(rsa_pem)
            ts = TrustStore.from_pem_file(pem_path)
            assert ts.keys == {}
            with pytest.raises(TrustError, match="Unknown key ID"):
                ts.verify("any-key", b"msg", b"sig")

    # ------------------------------------------------------------------
    # Signature verification on empty store fails closed
    # ------------------------------------------------------------------

    def test_verify_on_empty_store_always_fails(self):
        """Any metadata verification on empty store raises TrustError."""
        priv = Ed25519PrivateKey.generate()
        ts_empty = TrustStore()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "test-key")
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts_empty)

    # ------------------------------------------------------------------
    # Revoked key store: verify fails closed
    # ------------------------------------------------------------------

    def test_revoked_key_store_fails_closed(self):
        """Store with only revoked keys → verify raises TrustError."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("revoked", export_public_key_pem(priv.public_key(), "revoked"))
        ts.revoke_key("revoked")
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "revoked")
        with pytest.raises(TrustError, match="revoked"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Unknown key_id: store with other keys still rejects unknown
    # ------------------------------------------------------------------

    def test_unknown_key_id_on_populated_store_fails(self):
        """Store with keys A, B rejects verification for key C."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
        ts.add_key("key-b", export_public_key_pem(priv_b.public_key(), "key-b"))
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv_a, "key-c")
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # add_key with malformed PEM: raises TrustError (does not add partial)
    # ------------------------------------------------------------------

    def test_add_key_malformed_pem_fails_atomically(self):
        """Malformed PEM in add_key raises TrustError; store unchanged."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("good", export_public_key_pem(priv.public_key(), "good"))
        with pytest.raises(TrustError, match="Malformed PEM"):
            ts.add_key("bad", "not-a-pem")
        # Store unchanged
        assert len(ts.keys) == 1
        assert "good" in ts.keys
        assert "bad" not in ts.keys

    # ------------------------------------------------------------------
    # from_pem_file: truncated PEM block is skipped
    # ------------------------------------------------------------------

    def test_truncated_pem_block_skipped(self):
        """Truncated PEM (missing END) is skipped; remaining valid blocks loaded."""
        priv = Ed25519PrivateKey.generate()
        valid_pem = export_public_key_pem(priv.public_key(), "valid-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "truncated.pem"
            pem_path.write_text(
                "-----BEGIN PUBLIC KEY-----\n"  # truncated, no body, no END
                + valid_pem
            )
            ts = TrustStore.from_pem_file(pem_path)
            assert len(ts.keys) == 1
            assert "valid-key" in ts.keys
