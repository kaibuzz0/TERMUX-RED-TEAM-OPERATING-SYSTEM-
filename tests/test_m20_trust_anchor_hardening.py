"""Milestone 20 — Trust anchor hardening targeted tests.

Covers fingerprint binding, purpose enforcement, revocation,
malformed fingerprint rejection, and encrypted private-key compatibility.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)

from updates.signing import (
    export_public_key_pem,
    export_private_key_pem,
    generate_keypair,
    sign_metadata,
    verify_metadata,
)
from updates.trust import TrustStore, TrustedKey, TrustError, _compute_fingerprint
from updates.metadata import build_metadata




def _skip_if_no_symlink_support():
    """Skip tests that require creating symlinks when unprivileged on Windows."""
    import tempfile
    try:
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

class TestFingerprintBinding:
    """1-4. Fingerprint acceptance, mismatch, duplicate key_id, changed key."""

    def test_matching_fingerprint_accepted(self):
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "match-key")
        ts = TrustStore()
        ts.add_key("match-key", pub_pem)
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "match-key")
        verify_metadata(signed, ts)

    def test_fingerprint_mismatch_rejected(self):
        priv = Ed25519PrivateKey.generate()
        wrong_fp = "a" * 64
        pub_pem = priv.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        ts = TrustStore()
        with pytest.raises(TrustError, match="Fingerprint mismatch"):
            ts.add_key("bad-fp", pub_pem, fingerprint=wrong_fp)

    def test_changed_pem_under_same_key_id_rejected(self):
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        pem_a = export_public_key_pem(priv_a.public_key(), "same-id")
        pem_b = export_public_key_pem(priv_b.public_key(), "same-id")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(pem_a + "\n" + pem_b)
            with pytest.raises(TrustError, match="Duplicate key_id"):
                TrustStore.from_pem_file(path)

    def test_duplicate_key_id_with_different_key_rejected(self):
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("dup", export_public_key_pem(priv_a.public_key(), "dup"))
        with pytest.raises(TrustError, match="Duplicate key_id"):
            ts.add_key("dup", export_public_key_pem(priv_b.public_key(), "dup"))


class TestPurposeBinding:
    """5-6. Correct purpose accepted; wrong purpose rejected."""

    def test_release_purpose_accepted(self):
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "rel-key", purpose="release")
        ts = TrustStore()
        ts.add_key("rel-key", pub_pem, purpose="release")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "rel-key")
        verify_metadata(signed, ts, expected_purpose="release")

    def test_wrong_purpose_rejected(self):
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "rel-key", purpose="plugin")
        ts = TrustStore()
        ts.add_key("rel-key", pub_pem, purpose="plugin")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "rel-key")
        with pytest.raises(TrustError, match="purpose"):
            verify_metadata(signed, ts, expected_purpose="release")

    def test_release_verify_defaults_to_release_purpose(self):
        from release_engine.signing import verify_release_metadata
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "rel-key", purpose="release")
        ts = TrustStore()
        ts.add_key("rel-key", pub_pem, purpose="release")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "rel-key")
        verify_release_metadata(signed, ts)

    def test_plugin_purpose_on_release_verify_rejected(self):
        from release_engine.signing import verify_release_metadata
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "plug-key", purpose="plugin")
        ts = TrustStore()
        ts.add_key("plug-key", pub_pem, purpose="plugin")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "plug-key")
        with pytest.raises(TrustError, match="purpose"):
            verify_release_metadata(signed, ts)


class TestRevocation:
    """7. Revoked key rejected."""

    def test_revoked_key_rejected(self):
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("rev", export_public_key_pem(priv.public_key(), "rev"))
        ts.revoke_key("rev")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "rev")
        with pytest.raises(TrustError, match="revoked"):
            verify_metadata(signed, ts)


class TestMalformedFingerprint:
    """8. Malformed fingerprint rejected."""

    def test_malformed_fingerprint_rejected(self):
        priv = Ed25519PrivateKey.generate()
        raw = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
        ts = TrustStore()
        with pytest.raises(TrustError, match="Malformed fingerprint"):
            ts.add_key("mal", raw, fingerprint="not-hex")

    def test_malformed_fingerprint_in_pem_file_rejected(self):
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "file-key")
        # Corrupt the fingerprint line
        corrupted = pem.replace("fingerprint_sha256:", "fingerprint_sha256: bad")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(corrupted)
            with pytest.raises(TrustError, match="Malformed fingerprint"):
                TrustStore.from_pem_file(path)


class TestKeyGenerationCompatibility:
    """9-11. Existing primitive, encrypted PKCS#8 load."""

    def test_existing_generate_keypair_signs_and_verifies(self):
        priv, pub = generate_keypair()
        ts = TrustStore()
        ts.add_key("gen", export_public_key_pem(pub, "gen"))
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "gen")
        verify_metadata(signed, ts)

    def test_encrypted_pkcs8_load_supported(self):
        priv = Ed25519PrivateKey.generate()
        encrypted_pem = priv.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(b"fixture-pass-123")
        )
        loaded = load_pem_private_key(encrypted_pem, password=b"fixture-pass-123")
        assert isinstance(loaded, Ed25519PrivateKey)
        ts = TrustStore()
        ts.add_key("enc", export_public_key_pem(loaded.public_key(), "enc"))
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, loaded, "enc")
        verify_metadata(signed, ts)

    def test_unencrypted_pkcs8_load_supported(self):
        priv = Ed25519PrivateKey.generate()
        plain_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        loaded = load_pem_private_key(plain_pem, password=None)
        assert isinstance(loaded, Ed25519PrivateKey)


class TestDomainSeparation:
    """12. Release/plugin domain substitution rejected."""

    def test_plugin_key_on_release_verify_rejected(self):
        from release_engine.signing import verify_release_metadata
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("dom", export_public_key_pem(priv.public_key(), "dom", purpose="plugin"), purpose="plugin")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "dom")
        with pytest.raises(TrustError, match="purpose"):
            verify_release_metadata(signed, ts)


class TestInspection:
    """TrustedKey.inspect() returns safe read-only metadata."""

    def test_inspect_returns_fingerprint_and_purpose(self):
        priv = Ed25519PrivateKey.generate()
        fp = _compute_fingerprint(priv.public_key())
        tk = TrustedKey(key_id="k", public_key=priv.public_key(), role="release", fingerprint=fp)
        info = tk.inspect()
        assert info["key_id"] == "k"
        assert info["fingerprint"] == fp
        assert info["purpose"] == "release"
        assert info["status"] == "active"
        assert info["revoked_at"] is None

    def test_inspect_computes_fingerprint_when_empty(self):
        priv = Ed25519PrivateKey.generate()
        tk = TrustedKey(key_id="k", public_key=priv.public_key())
        info = tk.inspect()
        assert info["fingerprint"] == _compute_fingerprint(priv.public_key())


class TestSymlinkFailClosed:
    """Symlinked trust store continues to fail closed."""

    def test_symlink_trust_store_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.pem"
            link = Path(tmp) / "link.pem"
            priv = Ed25519PrivateKey.generate()
            real.write_text(export_public_key_pem(priv.public_key(), "s"))
            link.symlink_to(real)
            ts = TrustStore.from_pem_file(link)
            assert ts.keys == {}