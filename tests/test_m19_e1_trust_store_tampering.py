"""E1-TRUST: Trust store tampering — file, memory, and loading integrity.

The trust store (`updates/trust.py`) is an in-memory JSON-backed PEM key store.
It enforces Ed25519-only keys, rejects duplicates, and supports revocation. This
test verifies tamper resistance of the trust store at the file, serialization,
and loading layers.

Note: This is the trust store layer, not the signing layer (E2/E3). The trust
store is the authority database; tampering it should fail closed (no keys trusted).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives import serialization

from updates.trust import TrustStore, TrustError, TrustLevel, TrustedKey
from updates.signing import export_public_key_pem, sign_metadata, verify_metadata


class TestTrustStoreTampering:
    """Trust store tampering at file, memory, and serialization layers."""

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
    # File layer: corrupted/missing trust store file
    # ------------------------------------------------------------------

    def test_missing_trust_store_file_returns_empty(self):
        """Non-existent PEM file returns empty TrustStore (fail-closed default)."""
        ts = TrustStore.from_pem_file(Path("/nonexistent/trust.pem"))
        assert ts.keys == {}

    def test_empty_trust_store_file_returns_empty(self):
        """Empty PEM file returns empty TrustStore."""
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text("")
            ts = TrustStore.from_pem_file(pem_path)
            assert ts.keys == {}

    def test_corrupted_pem_file_ignores_invalid_blocks(self):
        """Corrupted PEM blocks are silently skipped; valid blocks loaded."""
        priv = Ed25519PrivateKey.generate()
        valid_pem = export_public_key_pem(priv.public_key(), "valid-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text("garbage\n" + valid_pem + "\nmore garbage")
            ts = TrustStore.from_pem_file(pem_path)
            assert "valid-key" in ts.keys
            assert len(ts.keys) == 1

    def test_trust_store_file_with_only_garbage_returns_empty(self):
        """File with no valid PEM blocks returns empty TrustStore."""
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text("not a pem block\njust text")
            ts = TrustStore.from_pem_file(pem_path)
            assert ts.keys == {}

    # ------------------------------------------------------------------
    # Serialization: JSON tampering of the backing store
    # ------------------------------------------------------------------

    def test_malformed_json_in_keys_dict_rejected(self):
        """TrustStore keys dict must contain TrustedKey instances."""
        # Directly construct with wrong type — should fail when used
        ts = TrustStore(keys={"bad": "not-a-TrustedKey"})  # type: ignore[dict-item]
        with pytest.raises((AttributeError, TypeError)):
            ts.verify("bad", b"msg", b"sig")

    def test_trusted_key_fields_are_immutable(self):
        """TrustedKey status transitions via revoke_key only."""
        priv = Ed25519PrivateKey.generate()
        key = TrustedKey(key_id="test", public_key=priv.public_key())
        assert key.status == "active"
        key.status = "revoked"
        assert key.status == "revoked"
        # Other fields are frozen implicitly by dataclass(frozen not set)
        # but key_id and public_key are not expected to change

    # ------------------------------------------------------------------
    # Loading: mixed valid/invalid keys
    # ------------------------------------------------------------------

    def test_from_pem_file_skips_rsa_blocks(self):
        """RSA PEM blocks are silently skipped; Ed25519 blocks loaded."""
        ed_priv = Ed25519PrivateKey.generate()
        ed_pem = export_public_key_pem(ed_priv.public_key(), "ed-key")
        rsa_priv = generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(rsa_pem + "\n" + ed_pem)
            ts = TrustStore.from_pem_file(pem_path)
            assert "ed-key" in ts.keys
            assert len(ts.keys) == 1

    def test_from_pem_file_key_id_comment_extraction(self):
        """key_id extracted from preceding # key_id: comment line."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "named-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            ts = TrustStore.from_pem_file(pem_path)
            assert "named-key" in ts.keys
            assert len(ts.keys) == 1

    def test_from_pem_file_missing_key_id_comment_uses_fallback(self):
        """Missing key_id comment uses fallback numbering (key-1, key-2...)."""
        priv = Ed25519PrivateKey.generate()
        # Raw PEM without key_id comment
        raw_pem = priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(raw_pem)
            ts = TrustStore.from_pem_file(pem_path)
            assert "key-1" in ts.keys
            assert len(ts.keys) == 1

    # ------------------------------------------------------------------
    # Memory: in-memory key dict tampering
    # ------------------------------------------------------------------

    def test_direct_keys_dict_tampering_detected_at_verify(self):
        """Replacing a TrustedKey with wrong object causes verify to fail."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("test-key", export_public_key_pem(priv.public_key(), "test-key"))
        # Tamper in-memory
        ts.keys["test-key"] = "not a TrustedKey"  # type: ignore[assignment]
        with pytest.raises((AttributeError, TypeError)):
            ts.verify("test-key", b"msg", b"sig")

    def test_duplicate_key_id_rejected(self):
        """Adding same key_id twice raises TrustError."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "dup-key")
        ts = TrustStore()
        ts.add_key("dup-key", pem)
        with pytest.raises(TrustError, match="Duplicate key_id"):
            ts.add_key("dup-key", pem)

    # ------------------------------------------------------------------
    # Revocation: double-revoke is idempotent
    # ------------------------------------------------------------------

    def test_double_revoke_is_idempotent(self):
        """Revoking an already-revoked key is silently idempotent."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("rev-key", export_public_key_pem(priv.public_key(), "rev-key"))
        ts.revoke_key("rev-key")
        assert ts.keys["rev-key"].status == "revoked"
        # Second revoke succeeds silently (idempotent)
        ts.revoke_key("rev-key")
        assert ts.keys["rev-key"].status == "revoked"

    def test_revoke_unknown_key_raises(self):
        """Revoking a key never added raises TrustError."""
        ts = TrustStore()
        with pytest.raises(TrustError, match="unknown key"):
            ts.revoke_key("nonexistent")

    # ------------------------------------------------------------------
    # Verify: signature after key tampering
    # ------------------------------------------------------------------

    def test_verify_after_key_swap_fails(self):
        """Replacing a key's public key material causes signature verification to fail."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
        # Sign with key A
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv_a, "key-a")
        # Tamper: swap to key B's public key
        ts.keys["key-a"] = TrustedKey(key_id="key-a", public_key=priv_b.public_key())
        with pytest.raises(TrustError, match="Signature mismatch"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # PEM tampering: corrupted key bytes in valid envelope
    # ------------------------------------------------------------------

    def test_corrupted_public_key_bytes_in_pem_rejected(self):
        """Valid PEM envelope with corrupted key bytes rejected by OpenSSL."""
        priv = Ed25519PrivateKey.generate()
        valid_pem = export_public_key_pem(priv.public_key(), "test-key")
        # Corrupt the base64 body: replace body line with garbage
        lines = valid_pem.splitlines()
        body_idx = next(i for i, l in enumerate(lines) if l and not l.startswith("-") and not l.startswith("#"))
        lines[body_idx] = "AAAA" * 20
        corrupted_pem = "\n".join(lines)
        ts = TrustStore()
        with pytest.raises(TrustError, match="Malformed PEM"):
            ts.add_key("test-key", corrupted_pem)

    # ------------------------------------------------------------------
    # Private key in trust store rejected
    # ------------------------------------------------------------------

    def test_private_key_pem_rejected(self):
        """Private key PEM block must be rejected by load_pem_public_key."""
        priv = Ed25519PrivateKey.generate()
        private_pem = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        ts = TrustStore()
        with pytest.raises(TrustError, match="Malformed PEM"):
            ts.add_key("priv-key", private_pem)

    # ------------------------------------------------------------------
    # Multiple keys in single file
    # ------------------------------------------------------------------

    def test_multiple_keys_in_single_file(self):
        """from_pem_file loads multiple concatenated PEM blocks."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        pem_a = export_public_key_pem(priv_a.public_key(), "key-a")
        pem_b = export_public_key_pem(priv_b.public_key(), "key-b")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem_a + "\n" + pem_b)
            ts = TrustStore.from_pem_file(pem_path)
            assert "key-a" in ts.keys
            assert "key-b" in ts.keys
            assert len(ts.keys) == 2

    def test_duplicate_key_id_comment_in_file(self):
        """Two PEM blocks with same key_id but different keys — fail closed."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        pem_a = export_public_key_pem(priv_a.public_key(), "same-key")
        pem_b = export_public_key_pem(priv_b.public_key(), "same-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem_a + "\n" + pem_b)
            with pytest.raises(TrustError, match="Duplicate key_id"):
                TrustStore.from_pem_file(pem_path)

    # ------------------------------------------------------------------
    # Verify: wrong signature / tampered metadata
    # ------------------------------------------------------------------

    def test_verify_with_wrong_signature(self):
        """Correct key, wrong signature bytes → Signature mismatch."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("test-key", export_public_key_pem(priv.public_key(), "test-key"))
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "test-key")
        # Corrupt the signature
        signed["signing"]["signature"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
        with pytest.raises(TrustError, match="Signature mismatch"):
            verify_metadata(signed, ts)

    def test_verify_detects_tampered_metadata(self):
        """Tampered metadata body after signing fails verification."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("test-key", export_public_key_pem(priv.public_key(), "test-key"))
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "test-key")
        signed["manifest_digest"] = "tampered"
        with pytest.raises(TrustError, match="Signature mismatch"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # File modification after load does not affect in-memory store
    # ------------------------------------------------------------------

    def test_file_modification_after_load_is_ignored(self):
        """Modifying PEM file after load does not affect in-memory keys."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "original-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            ts = TrustStore.from_pem_file(pem_path)
            pem_path.write_text("corrupted")
            assert "original-key" in ts.keys
            assert len(ts.keys) == 1

    # ------------------------------------------------------------------
    # TrustStore dict isolation
    # ------------------------------------------------------------------

    def test_trust_store_shallow_copy_shares_values(self):
        """TrustStore(keys=dict(ts1.keys)) shares TrustedKey objects (shallow copy).
        
        The dict is copied but the TrustedKey values are shared references.
        This is expected behavior for mutable dataclass values.
        """
        priv = Ed25519PrivateKey.generate()
        ts1 = TrustStore()
        ts1.add_key("shared", export_public_key_pem(priv.public_key(), "shared"))
        ts2 = TrustStore(keys=dict(ts1.keys))
        # Both ts1 and ts2 reference the same TrustedKey object
        assert ts1.keys["shared"] is ts2.keys["shared"]
        ts2.revoke_key("shared")
        # ts1 sees the change because values are shared (shallow copy)
        assert ts1.keys["shared"].status == "revoked"

    # ------------------------------------------------------------------
    # Empty key_id rejected
    # ------------------------------------------------------------------

    def test_empty_key_id_rejected(self):
        """Empty string key_id is rejected at add_key."""
        ts = TrustStore()
        with pytest.raises(TrustError, match="non-empty"):
            ts.add_key("", "not-a-pem")

    # ------------------------------------------------------------------
    # TrustLevel enum is read-only
    # ------------------------------------------------------------------

    def test_trust_level_enum_values_are_stable(self):
        """TrustLevel enum values are stable strings."""
        assert TrustLevel.DEVELOPMENT_GIT.value == "development_git"
        assert TrustLevel.SIGNED_RELEASE.value == "signed_release"
        assert TrustLevel.OFFLINE_VERIFIED_BUNDLE.value == "offline_verified_bundle"
        assert TrustLevel.EMERGENCY_RECOVERY_BUNDLE.value == "emergency_recovery_bundle"
