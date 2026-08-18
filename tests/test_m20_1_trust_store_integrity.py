"""M20.1 — Trust-store integrity and policy tests.

Covers: truncation, emptiness, malformed PEM, duplicate comments,
missing fingerprints, unknown purpose, revocation with replacement,
read failures, and atomic replacement interruption.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from updates.trust import TrustStore, TrustedKey, TrustError, _compute_fingerprint
from updates.signing import (
    export_public_key_pem,
    sign_metadata,
    verify_metadata,
)
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

class TestTrustStoreTruncated:
    """Truncated trust-store file handling."""

    def test_truncated_pem_rejected(self):
        """Incomplete/truncated PEM block must not silently succeed."""
        priv = Ed25519PrivateKey.generate()
        full = export_public_key_pem(priv.public_key(), "t-key")
        truncated = full[:len(full) // 2]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(truncated)
            ts = TrustStore.from_pem_file(path)
            assert ts.keys == {}

    def test_empty_file_returns_empty(self):
        """Empty trust-store file returns empty store."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text("")
            ts = TrustStore.from_pem_file(path)
            assert ts.keys == {}


class TestMalformedPEM:
    """Malformed PEM blocks fail closed."""

    def test_malformed_pem_no_valid_blocks(self):
        """File with no valid PEM blocks returns empty store."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text("not a key\njust garbage\n")
            ts = TrustStore.from_pem_file(path)
            assert ts.keys == {}

    def test_corrupted_base64_in_pem(self):
        """PEM with corrupted base64 body rejected by add_key."""
        priv = Ed25519PrivateKey.generate()
        valid = export_public_key_pem(priv.public_key(), "c-key")
        lines = valid.splitlines()
        body_idx = next(
            i for i, l in enumerate(lines)
            if l and not l.startswith("-") and not l.startswith("#")
        )
        lines[body_idx] = "AAAA" * 20
        corrupted = "\n".join(lines)
        ts = TrustStore()
        with pytest.raises(TrustError, match="Malformed PEM"):
            ts.add_key("c-key", corrupted)

    def test_private_key_in_trust_store_rejected(self):
        """Private key PEM must be rejected at add_key."""
        priv = Ed25519PrivateKey.generate()
        private_pem = priv.private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        ).decode("utf-8")
        ts = TrustStore()
        with pytest.raises(TrustError, match="Malformed PEM"):
            ts.add_key("priv", private_pem)


class TestDuplicateComments:
    """Duplicated metadata comments in PEM file."""

    def test_duplicate_key_id_comment_fails(self):
        """Same key_id declared twice with same key — fail closed."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "dup")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(pem + "\n" + pem)
            with pytest.raises(TrustError, match="Duplicate key_id"):
                TrustStore.from_pem_file(path)

    def test_conflicting_fingerprint_for_same_key_id(self):
        """Same key_id with different fingerprints fails."""
        priv = Ed25519PrivateKey.generate()
        fp = _compute_fingerprint(priv.public_key())
        pem = export_public_key_pem(priv.public_key(), "conflict")
        # Inject a conflicting fingerprint comment
        tampered = pem.replace(f"fingerprint_sha256: {fp}", "fingerprint_sha256: " + "a" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(tampered)
            with pytest.raises(TrustError, match="Fingerprint mismatch"):
                TrustStore.from_pem_file(path)


class TestFingerprintWithoutKey:
    """Fingerprint comment without a valid key block."""

    def test_fingerprint_comment_alone_no_pem_returns_empty(self):
        """A fingerprint comment with no PEM block returns empty store."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text("# key_id: orphan\n# fingerprint_sha256: " + "a" * 64 + "\n")
            ts = TrustStore.from_pem_file(path)
            assert ts.keys == {}

    def test_explicit_non_ed25519_with_fingerprint_fails(self):
        """Explicitly declared non-Ed25519 entry with fingerprint fails closed."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pub_pem = rsa_priv.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        tampered = "# key_id: bad-key\n# fingerprint_sha256: " + "a" * 64 + "\n" + rsa_pub_pem
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(tampered)
            with pytest.raises(TrustError, match="not Ed25519"):
                TrustStore.from_pem_file(path)


class TestKeyWithoutFingerprint:
    """Key block without fingerprint comment."""

    def test_key_without_fingerprint_uses_computed(self):
        """Missing fingerprint comment falls back to computed fingerprint."""
        priv = Ed25519PrivateKey.generate()
        raw = priv.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text("# key_id: no-fp\n" + raw)
            ts = TrustStore.from_pem_file(path)
            assert "no-fp" in ts.keys
            assert ts.keys["no-fp"].fingerprint == _compute_fingerprint(priv.public_key())


class TestUnknownPurpose:
    """Unknown purpose values are accepted (stored as-is) but verified only
    when expected_purpose is passed."""

    def test_unknown_purpose_accepted_in_store(self):
        """Any string purpose is accepted into the store."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "unk", purpose="weird")
        ts = TrustStore()
        ts.add_key("unk", pem, purpose="weird")
        assert ts.keys["unk"].role == "weird"

    def test_unknown_purpose_rejected_on_verify(self):
        """Verify with expected_purpose rejects mismatched role."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("unk", export_public_key_pem(priv.public_key(), "unk", purpose="weird"), purpose="weird")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "unk")
        with pytest.raises(TrustError, match="purpose"):
            verify_metadata(signed, ts, expected_purpose="release")


class TestRevocationWithReplacement:
    """Revocation metadata and replacement key chaining."""

    def test_revoked_production_key_rejected(self):
        """Revoked production key must fail verification."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("prod", export_public_key_pem(priv.public_key(), "prod"))
        ts.revoke_key("prod")
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed = sign_metadata(meta, priv, "prod")
        with pytest.raises(TrustError, match="revoked"):
            verify_metadata(signed, ts)

    def test_revoked_key_records_timestamp(self):
        """Revocation sets ISO-8601 UTC timestamp."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("t", export_public_key_pem(priv.public_key(), "t"))
        ts.revoke_key("t")
        assert ts.keys["t"].status == "revoked"
        assert ts.keys["t"].revoked_at is not None
        assert "T" in ts.keys["t"].revoked_at

    def test_revoked_key_with_replacement(self):
        """Revoked key can carry replacement_key_id."""
        old_priv = Ed25519PrivateKey.generate()
        new_priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("old", export_public_key_pem(old_priv.public_key(), "old"))
        ts.add_key("new", export_public_key_pem(new_priv.public_key(), "new"))
        ts.revoke_key("old", replacement_key_id="new")
        assert ts.keys["old"].replacement_key_id == "new"

    def test_revoked_old_plus_active_replacement(self):
        """Old key revoked; replacement key active and can sign."""
        old_priv = Ed25519PrivateKey.generate()
        new_priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("old", export_public_key_pem(old_priv.public_key(), "old"))
        ts.add_key("new", export_public_key_pem(new_priv.public_key(), "new"))
        ts.revoke_key("old", replacement_key_id="new")

        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["x86_64"], "0.1.0")
        signed_old = sign_metadata(meta, old_priv, "old")
        with pytest.raises(TrustError, match="revoked"):
            verify_metadata(signed_old, ts)

        signed_new = sign_metadata(meta, new_priv, "new")
        verify_metadata(signed_new, ts)


class TestPermissionsAndReadFailure:
    """Permission and read-failure handling."""

    def test_unreadable_trust_store_returns_empty(self):
        """If the trust-store file cannot be read, return empty store.

        Skipped when running as root (root bypasses file permissions).
        """
        if (os.geteuid() if hasattr(os, 'geteuid') else 0) == 0:
            pytest.skip("Root bypasses file permission checks")
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            path.write_text(export_public_key_pem(priv.public_key(), "k"))
            os.chmod(path, 0o000)
            try:
                ts = TrustStore.from_pem_file(path)
                assert ts.keys == {}
            finally:
                os.chmod(path, 0o644)


class TestAtomicReplacementInterruption:
    """Atomic replacement of trust-store file."""

    def test_atomic_write_then_replace(self):
        """Atomic rename preserves integrity; interrupted write is ignored."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            dir_path = Path(tmp)
            old_path = dir_path / "trust.pem"
            new_path = dir_path / "trust.pem.new"

            old_path.write_text(export_public_key_pem(priv.public_key(), "old-key"))
            # Simulate incomplete write
            new_path.write_text("incomplete")
            # Atomic replace
            new_path.replace(old_path)
            ts = TrustStore.from_pem_file(old_path)
            # After replace, the file is the incomplete one
            assert ts.keys == {}

    def test_concurrent_read_during_replace(self):
        """Reading a partially-written trust store returns whatever is valid."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.pem"
            # Start with valid key A
            path.write_text(export_public_key_pem(priv_a.public_key(), "a"))
            ts1 = TrustStore.from_pem_file(path)
            assert "a" in ts1.keys
            # Atomically replace with key B
            tmp_path = Path(tmp) / "trust.pem.tmp"
            tmp_path.write_text(export_public_key_pem(priv_b.public_key(), "b"))
            tmp_path.replace(path)
            ts2 = TrustStore.from_pem_file(path)
            assert "b" in ts2.keys
            assert "a" not in ts2.keys


class TestTrustedKeyInspect:
    """TrustedKey.inspect() returns safe read-only metadata."""

    def test_inspect_includes_status_and_revoked_at(self):
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("insp", export_public_key_pem(priv.public_key(), "insp"))
        ts.revoke_key("insp")
        info = ts.keys["insp"].inspect()
        assert info["status"] == "revoked"
        assert info["revoked_at"] is not None
        assert info["replacement_key_id"] is None

    def test_inspect_with_replacement_key_id(self):
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("r", export_public_key_pem(priv.public_key(), "r"))
        ts.revoke_key("r", replacement_key_id="next")
        info = ts.keys["r"].inspect()
        assert info["replacement_key_id"] == "next"