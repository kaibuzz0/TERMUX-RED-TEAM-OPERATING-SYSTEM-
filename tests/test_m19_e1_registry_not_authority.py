"""E1-REGISTRY-NOT-AUTHORITY: Production verification does not trust registry metadata alone.

The plugin SDK's `classify_signature()` performs metadata-level classification only
— it does NOT perform Ed25519 cryptographic verification against a trust store. A
manifest claiming `SIGNED_UNTRUSTED` or even `SIGNED_TRUSTED` in its signature section
has not been cryptographically verified.

Production verification (`verify_release_bundle`, `BundleVerifier.verify`) MUST
call `verify_metadata()` with an actual `TrustStore`. Registry metadata alone is
not authoritative for trust decisions.

This is a documentation and behavioral test: it proves the gap exists and that
production paths bridge it correctly.
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from plugin_sdk.signing import classify_signature, TrustState, SignatureMetadata
from plugin_sdk.registry import PluginRegistry
from plugin_sdk.manifest import load_manifest
from updates.trust import TrustStore, TrustError
from updates.bundle import create_tar_bundle
from release_engine.verifier import verify_release_bundle
from updates.signing import sign_metadata, verify_metadata


class TestRegistryMetadataNotTrusted:
    """Registry/classify_signature metadata is not cryptographic proof."""

    @staticmethod
    def _make_bundle(source, metadata, manifest=None):
        """Create a proper bundle with real file artifacts."""
        import hashlib
        from updates.bundle import create_tar_bundle
        if manifest:
            for entry in manifest:
                path = source / entry["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                data = b"artifact_data_for_" + entry["path"].encode()
                path.write_bytes(data)
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["size"] = len(data)
        return create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest or [], metadata)

    def test_classify_signature_does_not_verify_cryptographically(self):
        """classify_signature returns SIGNED_UNTRUSTED for any well-formed signature."""
        fake_manifest = {
            "schema_version": 1,
            "plugin": {"id": "test", "version": "1.0.0"},
            "signature": {
                "publisher_id": "fake-publisher",
                "signature_blob": "totally_fake_signature_not_base64_valid",
            },
        }
        result = classify_signature(fake_manifest)
        assert result.trust_state == TrustState.SIGNED_UNTRUSTED
        # It did NOT reject the manifest despite completely invalid signature data
        assert result.publisher_id == "fake-publisher"

    def test_classify_signature_returns_unsigned_for_no_sig(self):
        """Missing signature returns UNSIGNED, not an error."""
        manifest = {"schema_version": 1, "plugin": {"id": "test", "version": "1.0.0"}}
        result = classify_signature(manifest)
        assert result.trust_state == TrustState.UNSIGNED

    def test_classify_signature_source_has_no_verify_call(self):
        """Source inspection: classify_signature does not call verify_metadata."""
        src = inspect.getsource(classify_signature)
        assert "verify_metadata" not in src
        assert "public_key" not in src
        # "Ed25519" appears in the docstring but not in code body
        body_start = src.find('"""Classify signature section')
        body = src[body_start:]
        assert "verify" not in body.lower(), "classify_signature must not verify"
        assert "trust_store" not in src

    def test_registry_discover_trusts_manifest_without_verification(self):
        """Registry.discover loads manifest without cryptographic verification."""
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "plugin"
            stage.mkdir()
            manifest = {
                "schema_version": 1,
                "plugin": {"id": "test-plugin", "name": "Test", "version": "1.0.0", "sdk_version": "1.0", "type": "client", "entrypoint": "main.py"},
                "compatibility": {"minimum_hive_version": "1.0.0"},
                "permissions": {"requested_capabilities": []},
                "lifecycle": {"auto_start": False},
                "dependencies": {},
                "signature": {
                    "publisher_id": "attacker",
                    "signature_blob": "fake",
                },
            }
            (stage / "manifest.json").write_text(json.dumps(manifest))
            registry = PluginRegistry()
            entry = registry.discover(stage)
            # Registry accepted the manifest without verifying the signature
            assert entry.identity.plugin_id == "test-plugin"
            # classify_signature would say SIGNED_UNTRUSTED
            sig = classify_signature(entry.manifest)
            assert sig.trust_state == TrustState.SIGNED_UNTRUSTED

    def test_production_verify_rejects_fake_signature(self):
        """verify_release_bundle rejects fake signatures via TrustStore."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            work = Path(tmp) / "work"
            # Create manifest with proper digest
            manifest = [{"path": "file.txt", "hash": "abc123"}]
            self._make_bundle(source, {"schema_version": 1, "release": {"version": "1.0.0", "release_id": "test", "commit": "abc", "platforms": ["linux"], "architectures": ["x86_64"], "release_sequence": 1, "security_sequence": 1}, "manifest_digest": "placeholder", "signing": {"algorithm": "Ed25519", "key_id": "fake-key", "signature": "dGVzdA=="}}, manifest)
            bundle = source.parent / "bundle.tar.gz"
            ts = TrustStore()  # empty — no fake-key
            with pytest.raises(TrustError, match="Unknown key ID"):
                verify_release_bundle(bundle, work, ts)

    def test_real_signature_passes_production_verify(self):
        """Genuine Ed25519 signature passes verify_release_bundle."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            work = Path(tmp) / "work"
            manifest = [{"path": "file.txt", "hash": "abc123"}]
            import hashlib
            for entry in manifest:
                path = source / entry["path"]
                data = b"artifact_data_for_" + entry["path"].encode()
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
            from updates.bundle import create_tar_bundle
            create_tar_bundle(source, source.parent / "bundle.tar.gz", manifest, signed)
            bundle = source.parent / "bundle.tar.gz"

            ts = TrustStore()
            from updates.signing import export_public_key_pem
            ts.add_key("real-key", export_public_key_pem(priv.public_key(), "real-key"))
            result = verify_release_bundle(bundle, work, ts)
            assert result["verified"] is True

    def test_registry_metadata_must_not_bypass_trust_store(self):
        """Registry trust_state metadata cannot bypass TrustStore verification."""
        fake_manifest = {
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
            "signing": {
                "algorithm": "Ed25519",
                "key_id": "claimed-key",
                "signature": "dGVzdA==",
            },
        }
        # Registry/classify_signature doesn't verify release manifests,
        # but production verify_metadata requires TrustStore
        with pytest.raises(TrustError):
            verify_metadata(fake_manifest, TrustStore())
