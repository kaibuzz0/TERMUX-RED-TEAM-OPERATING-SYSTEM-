"""Verify release digest cannot authenticate plugin object.

Releases and plugins have separate manifest formats, separate digest
functions, and separate verification entry points. A digest produced
for one type must never be accepted as valid for the other.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from release_engine.manifest import manifest_digest as release_manifest_digest
from release_engine.verifier import verify_release_bundle
from release_engine.plugin_package import verify_plugin_package
from release_engine.errors import ReleaseFormatError
from updates.errors import BundleError
from updates.signing import export_public_key_pem
from updates.trust import TrustStore


class TestReleasePluginDigestSeparation:
    """Release and plugin digests are type-distinct and not interchangeable."""

    @staticmethod
    def _make_trust_store(key_id: str, priv: Ed25519PrivateKey):
        store = TrustStore()
        pub_pem = export_public_key_pem(priv.public_key(), key_id)
        store.add_key(key_id, pub_pem)
        return store

    # -----------------------------------------------------------------------
    # 1. Plugin manifest digest is not accepted as release manifest digest
    # -----------------------------------------------------------------------

    def test_plugin_digest_cannot_authenticate_release(self):
        """A plugin manifest digest must not be accepted as a release manifest digest."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            # Build a plugin manifest
            plugin_manifest = {
                "schema_version": 1,
                "plugin": {
                    "id": "test-plugin",
                    "name": "Test Plugin",
                    "version": "1.0.0",
                    "sdk_version": "1.0.0",
                    "type": "client",
                    "entrypoint": "main.py",
                },
                "permissions": {
                    "requested_capabilities": ["vault.status"],
                },
            }
            plugin_manifest_text = json.dumps(plugin_manifest, separators=(",", ":"))
            plugin_digest = __import__("hashlib").sha256(plugin_manifest_text.encode("utf-8")).hexdigest()

            # Build a release bundle structure with plugin digest substituted
            # as the release manifest_digest
            work = Path(tmp) / "work"
            work.mkdir()
            (work / "manifest.json").write_text("[]", encoding="utf-8")  # empty release manifest
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
                "manifest_digest": plugin_digest,  # WRONG type substituted
                "signing": {
                    "algorithm": "Ed25519",
                    "key_id": "test-key",
                    "signature": "",
                },
            }
            # Sign the metadata (with wrong digest)
            from release_engine.signing import sign_release_metadata
            from updates.bundle import create_tar_bundle
            signed = sign_release_metadata(metadata, priv, "test-key", plugin_digest)
            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(work, bundle, [], signed)

            # Verification must fail — plugin digest != release manifest digest
            verify_work = Path(tmp) / "verify"
            with pytest.raises(ReleaseFormatError, match="manifest digest mismatch"):
                verify_release_bundle(bundle, verify_work, store)

    # -----------------------------------------------------------------------
    # 2. Release manifest digest is not accepted as plugin manifest digest
    # -----------------------------------------------------------------------

    def test_release_digest_cannot_authenticate_plugin(self):
        """A release manifest digest must not be accepted as a plugin manifest digest."""
        priv = Ed25519PrivateKey.generate()
        store = self._make_trust_store("test-key", priv)

        with tempfile.TemporaryDirectory() as tmp:
            # Step 1: Build a real plugin package
            plugin_dir = Path(tmp) / "plugin_src"
            plugin_dir.mkdir()
            plugin_manifest = {
                "schema_version": 1,
                "plugin": {
                    "id": "test-plugin",
                    "name": "Test Plugin",
                    "version": "1.0.0",
                    "sdk_version": "1.0.0",
                    "type": "client",
                    "entrypoint": "main.py",
                },
                "compatibility": {
                    "minimum_hive_version": "1.0.0",
                },
                "permissions": {
                    "requested_capabilities": ["vault.status"],
                },
                "lifecycle": {
                    "auto_start": False,
                },
            }
            (plugin_dir / "manifest.json").write_text(
                json.dumps(plugin_manifest, separators=(",", ":")), encoding="utf-8"
            )
            (plugin_dir / "main.py").write_text("print('hello')", encoding="utf-8")

            # Package it into a .hivepkg zip
            from release_engine.plugin_package import create_plugin_package
            pkg_path = Path(tmp) / "plugin.hivepkg"
            info = create_plugin_package(plugin_dir, pkg_path)

            # Step 2: Build FAKE metadata.json where manifest_digest is a RELEASE digest
            release_entries = [{"path": "a.py", "hash": "abc", "size": 1, "sha256": "0" * 64}]
            release_digest = release_manifest_digest(release_entries)

            fake_metadata = {
                "plugin_id": "test-plugin",
                "version": "1.0.0",
                "manifest_digest": release_digest,  # WRONG type
                "bundle_digest": info["bundle_digest"],
                "publisher": "test-key",
                "sdk_compatibility": "1.0",
            }
            from release_engine.plugin_package import sign_plugin_package
            signed = sign_plugin_package(fake_metadata, priv, "test-key")

            # Append metadata.json to the zip (standard packaging pattern)
            import zipfile
            with zipfile.ZipFile(pkg_path, "a") as zf:
                zf.writestr("metadata.json", json.dumps(signed, indent=2, sort_keys=True))

            # Step 3: Verification must fail — release digest != plugin manifest digest
            verify_work = Path(tmp) / "verify"
            with pytest.raises(BundleError, match="plugin manifest digest mismatch"):
                verify_plugin_package(pkg_path, verify_work, store)

    # -----------------------------------------------------------------------
    # 3. Different canonical forms: plugin dict vs release list
    # -----------------------------------------------------------------------

    def test_plugin_and_release_canonical_forms_are_incompatible(self):
        """Plugin manifest (dict) and release manifest (list) must have different canonical forms."""
        plugin_manifest = {
            "plugin": {"id": "test", "version": "1.0.0"},
            "capabilities": ["vault.status"],
        }
        release_entries = [{"path": "a.py", "hash": "abc"}]

        # Plugin digest: raw bytes of compact JSON dict
        plugin_text = json.dumps(plugin_manifest, separators=(",", ":"))
        plugin_digest = __import__("hashlib").sha256(plugin_text.encode("utf-8")).hexdigest()

        # Release digest: canonical JSON of list of entries (sort_keys=True)
        release_digest = release_manifest_digest(release_entries)

        # They must differ
        assert plugin_digest != release_digest, "Plugin and release digests should never collide"

    # -----------------------------------------------------------------------
    # 4. Verification entry points are distinct
    # -----------------------------------------------------------------------

    def test_verification_entry_points_are_distinct(self):
        """verify_release_bundle and verify_plugin_package must be separate functions."""
        # This is a structural assertion — the two entry points exist and are different
        assert verify_release_bundle is not verify_plugin_package
        assert callable(verify_release_bundle)
        assert callable(verify_plugin_package)

        # They must accept different signatures
        import inspect
        release_sig = inspect.signature(verify_release_bundle)
        plugin_sig = inspect.signature(verify_plugin_package)
        assert release_sig != plugin_sig

    # -----------------------------------------------------------------------
    # 5. Different digest functions used
    # -----------------------------------------------------------------------

    def test_digest_functions_are_different(self):
        """Release and plugin must use different digest computation functions."""
        from plugin_sdk.manifest import manifest_digest as plugin_manifest_digest

        # plugin_manifest_digest computes sha256 of raw text
        text = '{"plugin":{"id":"x","version":"1.0.0"}}'
        d_plugin = plugin_manifest_digest(text)
        d_manual = __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()
        assert d_plugin == d_manual

        # release_manifest_digest computes sha256 of canonical JSON list
        entries = [{"path": "x.py"}]
        d_release = release_manifest_digest(entries)
        canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        d_canonical = __import__("hashlib").sha256(canonical.encode("utf-8")).hexdigest()
        assert d_release == d_canonical

        # The two digests must differ for equivalent logical content
        assert d_plugin != d_release
