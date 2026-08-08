"""E2/E3 — DOMAIN SEPARATION: Canonical JSON binds signature to object structure.

The system does not use an explicit domain prefix (e.g., "domain":"release").
Instead, domain separation is implicit: the canonical JSON serialization
includes ALL object keys sorted recursively. A release metadata dict has a
"release" block; a plugin manifest has a "plugin" block. The canonical bytes
differ, so a signature over one object type is invalid for another.

These tests document and verify that structural domain separation is already
provided by the existing canonical_json / verify_metadata design.
"""

from __future__ import annotations

import json

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.metadata import canonical_json
from updates.signing import sign_metadata, verify_metadata
from updates.trust import TrustStore, TrustError


class TestDomainSeparation:
    """Verify implicit domain separation via canonical JSON structure."""

    def test_canonical_json_includes_all_keys(self):
        """canonical_json serializes all keys; none are elided."""
        data = {"z": 1, "a": {"y": 2, "x": 3}, "b": [9, 8, 7]}
        out = canonical_json(data)
        assert '"a"' in out
        assert '"x"' in out
        assert '"y"' in out
        assert '"z"' in out
        assert '"b"' in out

    def test_canonical_json_sorts_keys(self):
        """canonical_json sorts keys deterministically."""
        data1 = {"z": 1, "a": 2}
        data2 = {"a": 2, "z": 1}
        assert canonical_json(data1) == canonical_json(data2)

    def test_canonical_json_rejects_floats(self):
        """Floats are rejected in canonical JSON — not reliably canonical."""
        from updates.errors import BundleError
        with pytest.raises(BundleError, match="Float values are not permitted"):
            canonical_json({"value": 1.5})

    def test_release_and_plugin_produce_different_canonical_bytes(self):
        """Release metadata and plugin manifest produce different canonical bytes."""
        release = {
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
        plugin = {
            "schema_version": 1,
            "plugin": {"id": "test", "version": "1.0.0", "author_key_id": "key"},
            "files": [],
        }
        release_bytes = canonical_json(release)
        plugin_bytes = canonical_json(plugin)
        assert release_bytes != plugin_bytes
        # Verify they are genuinely different bytes, not just key ordering
        assert "release" in release_bytes
        assert "plugin" in plugin_bytes

    def test_signature_is_bound_to_full_canonical_structure(self):
        """Ed25519 signature is computed over full canonical JSON, not a subset."""
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
        signed = sign_metadata(metadata, priv, "key-1")
        # The signature is over canonical JSON of the metadata dict
        # with algorithm, key_id, and signature blanked out.
        # Changing ANY field in the metadata invalidates the signature.
        signed["release"]["version"] = "2.0.0"
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed, ts)

    def test_no_domain_prefix_in_canonical_json(self):
        """Canonical JSON does not inject a synthetic domain prefix.

        Domain separation is structural (different object shapes), not
        explicit. This test documents the design choice.
        """
        release = {"schema_version": 1, "release": {"version": "1.0.0"}}
        out = canonical_json(release)
        assert "domain" not in out
        # Separation comes from the fact that release has "release" key
        # and plugin has "plugin" key, producing different canonical bytes.

    def test_verify_metadata_does_not_accept_partial_match(self):
        """Even a single byte difference in canonical JSON invalidates sig."""
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
        signed = sign_metadata(metadata, priv, "key-1")
        # Re-canonicalize with a tiny difference (extra whitespace not allowed,
        # but key order change would change bytes)
        signed["manifest_digest"] = "abc124"  # one char difference
        ts = TrustStore()
        from updates.signing import export_public_key_pem
        ts.add_key("key-1", export_public_key_pem(priv.public_key(), "key-1"))
        with pytest.raises(TrustError, match="Signature mismatch|Invalid signature"):
            verify_metadata(signed, ts)
