"""E2/E3 — KEY / ALGORITHM DOWNGRADE: Ed25519 is strictly enforced.

An attacker may attempt to downgrade the signing algorithm to a weaker
or non-existent scheme (RSA, SHA256, "none", empty string). The system
must reject all non-Ed25519 algorithms at every verification layer.

Tests cover:
  * verify_metadata() rejects algorithm downgrade
  * BundleVerifier rejects non-Ed25519 metadata
  * TrustStore rejects non-Ed25519 key types
  * Source inspection confirms no algorithm negotiation or fallback
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.signing import sign_metadata, verify_metadata
from updates.trust import TrustStore, TrustError
from updates.verifier import BundleVerifier
from updates.errors import BundleError
from updates.bundle import create_tar_bundle


class TestAlgorithmDowngradeRejection:
    """Only Ed25519 is accepted; any algorithm downgrade fails closed."""

    def _sample_metadata(self):
        return {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test",
                "commit": "abc",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }

    # ------------------------------------------------------------------
    # verify_metadata layer
    # ------------------------------------------------------------------

    def test_verify_metadata_rejects_rsa_algorithm(self):
        """Algorithm 'RSA' rejected by verify_metadata."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        signed["signing"]["algorithm"] = "RSA"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_rejects_sha256_algorithm(self):
        """Algorithm 'SHA256' rejected by verify_metadata."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        signed["signing"]["algorithm"] = "SHA256"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_rejects_none_algorithm(self):
        """Algorithm 'none' rejected by verify_metadata."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        signed["signing"]["algorithm"] = "none"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_rejects_empty_algorithm(self):
        """Algorithm '' rejected by verify_metadata."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        signed["signing"]["algorithm"] = ""
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_rejects_missing_algorithm(self):
        """Missing algorithm field rejected by verify_metadata."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        del signed["signing"]["algorithm"]
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_rejects_ed25519_lowercase(self):
        """Algorithm 'ed25519' (lowercase) rejected — must be exact 'Ed25519'."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        signed["signing"]["algorithm"] = "ed25519"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_verify_metadata_accepts_exact_ed25519(self):
        """Algorithm 'Ed25519' (exact case) accepted."""
        priv = Ed25519PrivateKey.generate()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "key-1")
        assert signed["signing"]["algorithm"] == "Ed25519"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        verify_metadata(signed, ts)  # does not raise

    # ------------------------------------------------------------------
    # BundleVerifier layer
    # ------------------------------------------------------------------

    def test_bundle_verifier_rejects_downgrade_in_metadata(self):
        """BundleVerifier.verify raises TrustError on algorithm downgrade."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            work = Path(tmp) / "work"
            import hashlib
            manifest = [{"path": "file.txt", "hash": "abc123"}]
            for entry in manifest:
                path = source / entry["path"]
                data = b"artifact_data"
                path.write_bytes(data)
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["size"] = len(data)
            from release_engine.manifest import manifest_digest
            digest = manifest_digest(manifest)
            metadata = {
                "schema_version": 1,
                "release": {
                    "version": "1.0.0",
                    "release_id": "test",
                    "commit": "abc",
                    "platforms": ["linux"],
                    "architectures": ["x86_64"],
                    "release_sequence": 1,
                    "security_sequence": 1,
                },
                "manifest_digest": digest,
            }
            from updates.signing import sign_metadata as _sign
            signed = _sign(metadata, priv, "real-key")
            signed["signing"]["algorithm"] = "RSA"  # downgrade attack
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
            verifier = BundleVerifier(
                trust_store=ts,
                platform="linux",
                architecture="x86_64",
            )
            with pytest.raises(TrustError, match="Unsupported signing algorithm"):
                verifier.verify(bundle, work)

    # ------------------------------------------------------------------
    # Source inspection: no algorithm negotiation or fallback
    # ------------------------------------------------------------------

    def test_verify_metadata_has_exact_string_comparison(self):
        """verify_metadata uses exact string equality, not starts_with or in."""
        src = inspect.getsource(verify_metadata)
        # Must be exact equality check, not fuzzy matching
        assert 'algorithm != "Ed25519"' in src or '!= "Ed25519"' in src
        assert "startswith" not in src.lower()
        assert "in algorithms" not in src.lower()

    def test_sign_metadata_always_uses_ed25519(self):
        """sign_metadata unconditionally sets algorithm to Ed25519."""
        src = inspect.getsource(sign_metadata)
        assert '"algorithm": "Ed25519"' in src or "algorithm='Ed25519'" in src
        # No parameter to change algorithm
        assert "algorithm" not in inspect.signature(sign_metadata).parameters

    def test_no_algorithm_negotiation_in_source(self):
        """No algorithm negotiation, fallback, or dynamic algorithm selection."""
        import updates.signing as signing_module
        src = inspect.getsource(signing_module)
        assert "negotiate" not in src.lower()
        assert "fallback" not in src.lower()
        assert "supported_algorithms" not in src.lower()
        assert "algorithm_list" not in src.lower()

    # ------------------------------------------------------------------
    # Trust store: key type downgrade
    # ------------------------------------------------------------------

    def test_trust_store_rejects_rsa_pem(self):
        """RSA public key PEM rejected by from_pem_file."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        with tempfile.TemporaryDirectory() as tmp:
            pem_file = Path(tmp) / "trust.pem"
            pem_file.write_text(f"# key-id=rsa-key\n{rsa_pem}")
            ts = TrustStore.from_pem_file(pem_file)
            assert len(ts.keys) == 0

    def test_trust_store_rejects_ecdsa_pem(self):
        """ECDSA public key PEM rejected by from_pem_file."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        ec_key = ec.generate_private_key(ec.SECP256R1())
        ec_pem = ec_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        with tempfile.TemporaryDirectory() as tmp:
            pem_file = Path(tmp) / "trust.pem"
            pem_file.write_text(f"# key-id=ec-key\n{ec_pem}")
            ts = TrustStore.from_pem_file(pem_file)
            assert len(ts.keys) == 0
