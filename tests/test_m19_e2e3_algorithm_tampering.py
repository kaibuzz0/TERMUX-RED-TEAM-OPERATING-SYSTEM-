"""E2/E3 — ALGORITHM IDENTIFIER TAMPERING: Explicit tampering vectors.

An attacker who controls metadata may tamper with the algorithm identifier
to bypass verification. This test covers injection, encoding, and format-level
attacks against the algorithm field specifically.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.signing import sign_metadata, verify_metadata
from updates.trust import TrustStore, TrustError
from updates.bundle import create_tar_bundle
from release_engine.verifier import verify_release_bundle
from updates.errors import BundleError


class TestAlgorithmIdentifierTampering:
    """Tampering with the algorithm identifier must always fail closed."""

    def _make_signed_metadata(self, key_id="test-key"):
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, key_id)
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key(key_id, export_public_key_pem(priv.public_key(), key_id))
        return signed, ts, priv

    # ------------------------------------------------------------------
    # Case manipulation
    # ------------------------------------------------------------------

    def test_tampered_algorithm_unknown_arbitrary(self):
        """Algorithm 'SuperSecureAlgo9000' rejected — arbitrary unknown value."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "SuperSecureAlgo9000"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_all_uppercase(self):
        """Algorithm 'ED25519' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "ED25519"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_mixed_case(self):
        """Algorithm 'Ed25519' with trailing dot rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519."
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_with_leading_space(self):
        """Algorithm ' Ed25519' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = " Ed25519"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_with_trailing_space(self):
        """Algorithm 'Ed25519 ' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519 "
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_with_null_byte(self):
        """Algorithm 'Ed25519\x00' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519\x00"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_with_newline(self):
        """Algorithm 'Ed25519\n' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519\n"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Prefix / suffix injection
    # ------------------------------------------------------------------

    def test_tampered_algorithm_prefixed_with_ed25519(self):
        """Algorithm 'Ed25519-Ph' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519-Ph"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_suffixed_with_hash(self):
        """Algorithm 'Ed25519-SHA512' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519-SHA512"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_with_slash(self):
        """Algorithm 'Ed25519/RSA' rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = "Ed25519/RSA"
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Type confusion
    # ------------------------------------------------------------------

    def test_tampered_algorithm_as_integer(self):
        """Algorithm as integer 1 rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = 1
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_as_none(self):
        """Algorithm as None rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = None
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_as_list(self):
        """Algorithm as list ['Ed25519'] rejected."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algorithm"] = ["Ed25519"]
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Signing block structure tampering
    # ------------------------------------------------------------------

    def test_tampered_algorithm_field_renamed(self):
        """Algorithm moved to 'algo' field — verify reads 'algorithm'."""
        signed, ts, _ = self._make_signed_metadata()
        signed["signing"]["algo"] = signed["signing"].pop("algorithm")
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_algorithm_field_missing_but_block_present(self):
        """Signing block present but algorithm field absent — rejected."""
        signed, ts, _ = self._make_signed_metadata()
        # Remove only algorithm, leave key_id and signature
        del signed["signing"]["algorithm"]
        with pytest.raises(TrustError, match="Unsupported signing algorithm"):
            verify_metadata(signed, ts)

    def test_tampered_signature_field_missing(self):
        """Algorithm present but signature field absent — rejected."""
        signed, ts, _ = self._make_signed_metadata()
        del signed["signing"]["signature"]
        with pytest.raises(TrustError, match="Missing signing metadata"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Key ID substitution
    # ------------------------------------------------------------------

    def test_tampered_key_id_to_unknown(self):
        """Signature valid for key A but key_id claims key B (unknown)."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        # Attacker changes key_id to unknown key
        signed["signing"]["key_id"] = "fake-key"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    def test_tampered_key_id_to_different_valid_key(self):
        """Signature valid for key A but key_id claims key B (both valid)."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv_a, "key-a")
        # Attacker changes key_id to key-b (different key was used for signing)
        signed["signing"]["key_id"] = "key-b"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
        ts.add_key("key-b", export_public_key_pem(priv_b.public_key(), "key-b"))
        # Signature was made with key-a, but metadata claims key-b
        with pytest.raises(TrustError, match="Signature mismatch"):
            verify_metadata(signed, ts)

    def test_tampered_key_id_empty(self):
        """Signature with empty key_id rejected."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        signed["signing"]["key_id"] = ""
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Missing signing metadata"):
            verify_metadata(signed, ts)

    def test_tampered_key_id_with_whitespace(self):
        """Signature with whitespace-padded key_id rejected."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        # Whitespace-padded key_id is a different key_id
        signed["signing"]["key_id"] = " real-key"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    def test_bundle_key_id_substitution_detected(self):
        """End-to-end: bundle with swapped key_id fails verification."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
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
            signed = _sign(metadata, priv_a, "key-a")
            # Attacker swaps key_id to key-b
            signed["signing"]["key_id"] = "key-b"
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
            ts.add_key("key-b", export_public_key_pem(priv_b.public_key(), "key-b"))
            with pytest.raises(TrustError, match="Signature mismatch"):
                verify_release_bundle(bundle, work, ts)

    # ------------------------------------------------------------------
    # Signature material substitution
    # ------------------------------------------------------------------

    def test_tampered_signature_bytes_replaced_with_garbage(self):
        """Valid metadata but signature bytes replaced with random data."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        import base64
        signed["signing"]["signature"] = base64.urlsafe_b64encode(b"garbage_signature_not_valid").decode("ascii")
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed, ts)

    def test_tampered_signature_bytes_truncated(self):
        """Valid metadata but signature bytes truncated."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        import base64
        original = base64.urlsafe_b64decode(signed["signing"]["signature"].encode("ascii"))
        truncated = base64.urlsafe_b64encode(original[:32]).decode("ascii")  # half the sig
        signed["signing"]["signature"] = truncated
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises((TrustError, ValueError)):
            verify_metadata(signed, ts)

    def test_tampered_signature_from_different_message(self):
        """Signature bytes from a different message (same key)."""
        priv = Ed25519PrivateKey.generate()
        metadata_a = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test-a",
                "commit": "abc",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }
        metadata_b = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test-b",
                "commit": "abc",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "def456",
        }
        signed_a = sign_metadata(metadata_a, priv, "real-key")
        signed_b = sign_metadata(metadata_b, priv, "real-key")
        # Attacker puts signature from B onto metadata A
        signed_a["signing"]["signature"] = signed_b["signing"]["signature"]
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed_a, ts)

    def test_tampered_signature_base64_corrupted(self):
        """Signature base64 encoding corrupted."""
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        signed["signing"]["signature"] = "!!!invalid_base64!!!"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises((TrustError, ValueError)):
            verify_metadata(signed, ts)

    def test_tampered_signature_swapped_from_different_key(self):
        """Signature bytes from key B applied to message signed with key A."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed_a = sign_metadata(metadata, priv_a, "key-a")
        signed_b = sign_metadata(metadata, priv_b, "key-b")
        # Attacker replaces signature with one from key B, keeps key_id as key-a
        signed_a["signing"]["signature"] = signed_b["signing"]["signature"]
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
        ts.add_key("key-b", export_public_key_pem(priv_b.public_key(), "key-b"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed_a, ts)

    def test_bundle_signature_material_substitution(self):
        """End-to-end: bundle with replaced signature bytes fails."""
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
            import base64
            signed["signing"]["signature"] = base64.urlsafe_b64encode(b"replaced").decode("ascii")
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
            with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
                verify_release_bundle(bundle, work, ts)

    def test_valid_signature_reused_across_object_type(self):
        """Signature over release metadata cannot authenticate plugin metadata.

        Even with the same key_id and algorithm, the canonical JSON bytes
        differ between object types, so signature verification fails.
        """
        priv = Ed25519PrivateKey.generate()
        # Release metadata (canonical JSON includes release block)
        release_metadata = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test-release",
                "commit": "abc",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }
        # Plugin metadata (different canonical JSON — plugin block, no release block)
        plugin_metadata = {
            "schema_version": 1,
            "plugin": {"id": "test", "version": "1.0.0", "author_key_id": "real-key"},
            "files": [],
        }
        # Sign the release metadata
        from updates.signing import sign_metadata as _sign
        signed_release = _sign(release_metadata, priv, "real-key")
        # Attacker tries to reuse that signature on plugin metadata
        signed_plugin = dict(plugin_metadata)
        signed_plugin["signing"] = signed_release["signing"]
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed_plugin, ts)

    def test_cross_protocol_signature_substitution(self):
        """A signature from a completely different protocol (e.g., a raw
        JSON Web Token, a PGP signature block, or a custom format) cannot
        be substituted into the metadata signing block.

        The verify_metadata function canonicalizes the entire metadata
        and checks algorithm == "Ed25519"; any foreign signature format
        is rejected.
        """
        priv = Ed25519PrivateKey.generate()
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
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "real-key")
        # Attacker replaces the Ed25519 signature with a fake PGP-like block
        signed["signing"]["signature"] = (
            "LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0=\n"  # base64 of "-----BEGIN PGP SIGNATURE-----"
        )
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
        with pytest.raises((TrustError, ValueError)):
            verify_metadata(signed, ts)

    def test_release_signature_cannot_authenticate_plugin(self):
        """A release metadata signature cannot be reused to authenticate a
        plugin manifest, even with identical key_id and algorithm.

        The canonical JSON bytes differ: release metadata contains a
        'release' block with platform/architecture data, while plugin
        metadata contains a 'plugin' block with id/version/author_key_id.
        verify_metadata() canonicalizes the full dict, so substitution
        across object types produces a signature mismatch.
        """
        priv = Ed25519PrivateKey.generate()
        from updates.signing import export_public_key_pem, sign_metadata as _sign
        # Release metadata (the real thing signed by release tooling)
        release_metadata = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "hive-1.0.0",
                "commit": "deadbeef",
                "platforms": ["linux", "android"],
                "architectures": ["x86_64", "aarch64"],
                "release_sequence": 42,
                "security_sequence": 7,
            },
            "manifest_digest": "abcd1234" * 4,
        }
        signed_release = _sign(release_metadata, priv, "release-key")
        # Plugin manifest (attacker reuses the release signature here)
        plugin_manifest = {
            "schema_version": 1,
            "plugin": {
                "id": "malicious-plugin",
                "version": "1.0.0",
                "author_key_id": "release-key",
            },
            "files": [{"path": "exploit.py", "sha256": "a" * 64, "size": 1024}],
        }
        # Copy the signing block from the release onto the plugin
        plugin_with_sig = dict(plugin_manifest)
        plugin_with_sig["signing"] = signed_release["signing"]
        ts = TrustStore()
        ts.add_key("release-key", export_public_key_pem(priv.public_key(), "release-key"))
        # The signature was computed over release canonical bytes,
        # but verify_metadata canonicalizes plugin bytes.
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(plugin_with_sig, ts)

    def test_plugin_signature_cannot_authenticate_release(self):
        """A plugin manifest signature cannot be reused to authenticate
        release metadata. The canonical JSON bytes differ (plugin block
        vs release block), so substitution fails signature verification.
        """
        priv = Ed25519PrivateKey.generate()
        from updates.signing import export_public_key_pem, sign_metadata as _sign
        # Plugin metadata signed by author
        plugin_metadata = {
            "schema_version": 1,
            "plugin": {
                "id": "legit-plugin",
                "version": "1.0.0",
                "author_key_id": "plugin-key",
            },
            "files": [{"path": "main.py", "sha256": "b" * 64, "size": 2048}],
        }
        signed_plugin = _sign(plugin_metadata, priv, "plugin-key")
        # Release metadata (attacker reuses the plugin signature here)
        release_metadata = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "hive-1.0.0",
                "commit": "cafebabe",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "beef" * 16,
        }
        # Copy the signing block from the plugin onto the release
        release_with_sig = dict(release_metadata)
        release_with_sig["signing"] = signed_plugin["signing"]
        ts = TrustStore()
        ts.add_key("plugin-key", export_public_key_pem(priv.public_key(), "plugin-key"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(release_with_sig, ts)

    def test_tampered_signing_block_removed(self):
        """Entire signing block removed — missing algorithm."""
        signed, ts, _ = self._make_signed_metadata()
        del signed["signing"]
        with pytest.raises(TrustError, match="Unsupported signing algorithm|Missing signing"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Bundle-level tampering (end-to-end)
    # ------------------------------------------------------------------

    def test_bundle_with_tampered_algorithm_field(self):
        """Bundle with Ed25519 sig but tampered algorithm in metadata."""
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
            signed["signing"]["algorithm"] = "RSA"  # tampered after signing
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
            with pytest.raises(TrustError, match="Unsupported signing algorithm"):
                verify_release_bundle(bundle, work, ts)

    def test_bundle_algorithm_field_case_spoofing(self):
        """Bundle with lowercase 'ed25519' algorithm rejected end-to-end."""
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
            signed["signing"]["algorithm"] = "ed25519"  # lowercase
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
            with pytest.raises(TrustError, match="Unsupported signing algorithm"):
                verify_release_bundle(bundle, work, ts)
