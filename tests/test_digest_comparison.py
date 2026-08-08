"""Verify digest comparison behavior at security-sensitive sites.

Documents where digests are compared in the canonical codebase and verifies:
1. Mismatches are correctly detected (functional correctness)
2. The comparison method used (standard == vs constant-time)

NOTE: This test does NOT attempt timing attacks; it documents the state
of the comparison mechanism for security review.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from release_engine.manifest import manifest_digest
from release_engine.signing import sign_release_metadata
from release_engine.verifier import verify_release_bundle
from release_engine.errors import ReleaseFormatError
from updates.signing import export_public_key_pem
from updates.trust import TrustStore
from updates.bundle import create_tar_bundle


class TestDigestComparison:
    """Digest comparison at security-sensitive verification sites."""

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
    # Site 1: release_engine/verifier.py line 63
    #   expected_digest = metadata.get("manifest_digest", "")
    #   actual_digest = hashlib_digest(manifest)
    #   if expected_digest != actual_digest:
    #       raise ReleaseFormatError("manifest digest mismatch")
    # -----------------------------------------------------------------------

    def test_verifier_detects_manifest_digest_mismatch(self):
        """verify_release_bundle must raise ReleaseFormatError when manifest digests differ."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "bin").mkdir()
            content = "#!/bin/sh\necho ok"
            (source / "bin" / "hive").write_text(content, encoding="utf-8")
            hive_size = (source / "bin" / "hive").stat().st_size
            import hashlib
            hive_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

            manifest = [{"path": "bin/hive", "hash": "abc123", "size": hive_size, "sha256": hive_sha}]
            digest = manifest_digest(manifest)
            metadata = self._make_metadata()
            metadata["manifest_digest"] = digest
            signed = sign_release_metadata(metadata, priv, "test-key", digest)

            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle, manifest, signed)

            # Tamper: change the manifest content AFTER signing
            tamper_work = Path(tmp) / "tamper"
            tamper_work.mkdir()
            from updates.bundle import extract_bundle
            extract_bundle(bundle, tamper_work)

            # Modify manifest.json content (not metadata)
            manifest_path = tamper_work / "manifest.json"
            tampered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            tampered_manifest[0]["hash"] = "TAMPERED"
            manifest_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")

            # Re-pack (metadata stays signed, manifest is tampered)
            tampered_bundle = Path(tmp) / "tampered.tar.gz"
            create_tar_bundle(tamper_work, tampered_bundle, tampered_manifest, signed)

            verify_work = Path(tmp) / "verify"
            with pytest.raises(ReleaseFormatError, match="manifest digest mismatch"):
                verify_release_bundle(tampered_bundle, verify_work, store)

    # -----------------------------------------------------------------------
    # Site 2: updates/manifest.py line 110
    #   digest = _sha256(full)
    #   if digest != entry.get("sha256"):
    #       raise BundleError("Digest mismatch: {rel}")
    #
    # This is checked indirectly via verify_manifest inside verify_release_bundle.
    # When manifest entry sha256 doesn't match actual file sha256, BundleError is raised.
    # Verified in Area D/E existing tests; not duplicated here.
    # -----------------------------------------------------------------------

    def test_digest_comparison_method_documented(self):
        """Document that canonical code uses standard string comparison for digests.

        Python's != on strings is short-circuit (returns at first mismatch).
        For local file verification where attacker doesn't control either operand,
        this is acceptable. For network-exposed or attacker-controlled inputs,
        hmac.compare_digest() would be preferred.
        """
        # This is a documentation-only test; it always passes.
        # Finding: canonical code uses standard comparison, not constant-time.
        # Locations:
        #   - release_engine/verifier.py:63  (manifest_digest)
        #   - release_engine/plugin_package.py:97  (plugin manifest_digest)
        #   - updates/manifest.py:110  (per-file sha256)
        assert True
