"""Tests for Ed25519 release signing."""

from __future__ import annotations

import base64
import unittest

from updates import generate_keypair, sign_metadata, verify_metadata, TrustStore, build_metadata
from updates.errors import TrustError


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.private, self.public = generate_keypair()
        self.meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0")

    def test_valid_signature(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        pem = export_public_key_pem(self.public, "key1")
        trust.add_key("key1", pem)
        verify_metadata(signed, trust)

    def test_wrong_public_key(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        _, other_pub = generate_keypair()
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        pem = export_public_key_pem(other_pub, "key1")
        trust.add_key("key1", pem)
        with self.assertRaises(TrustError):
            verify_metadata(signed, trust)

    def test_modified_metadata(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        signed["release"]["version"] = "2.0.0"
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        pem = export_public_key_pem(self.public, "key1")
        trust.add_key("key1", pem)
        with self.assertRaises(TrustError):
            verify_metadata(signed, trust)


    def test_signing_deterministic(self):
        signed1 = sign_metadata(self.meta, self.private, "key1")
        signed2 = sign_metadata(self.meta, self.private, "key1")
        self.assertEqual(signed1["signing"]["signature"], signed2["signing"]["signature"])

    def test_signature_field_excluded(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        # The signature bytes are computed over a payload whose signature field is empty.
        from updates.metadata import canonical_json
        payload = dict(signed)
        payload["signing"] = {"algorithm": "Ed25519", "key_id": "key1", "signature": ""}
        message = canonical_json(payload).encode("utf-8")
        sig = base64.urlsafe_b64decode(signed["signing"]["signature"].encode("ascii"))
        pub = self.private.public_key()
        pub.verify(sig, message)

    def test_whitespace_does_not_affect_signature(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        import json
        reloaded = json.loads(json.dumps(signed, indent=2))
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        trust.add_key("key1", export_public_key_pem(self.public, "key1"))
        verify_metadata(reloaded, trust)

    def test_floats_rejected_in_canonical_json(self):
        from updates.metadata import canonical_json
        with self.assertRaises(Exception):
            canonical_json({"value": 1.5})


    def test_empty_trust_store_fails_verification(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        trust = TrustStore()
        with self.assertRaises(TrustError):
            verify_metadata(signed, trust)

    def test_unknown_key_id_fails_closed(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        trust.add_key("key2", export_public_key_pem(self.public, "key2"))
        with self.assertRaises(TrustError):
            verify_metadata(signed, trust)

    def test_revoked_key_fails_verification(self):
        signed = sign_metadata(self.meta, self.private, "key1")
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        trust.add_key("key1", export_public_key_pem(self.public, "key1"))
        trust.revoke_key("key1")
        with self.assertRaises(TrustError):
            verify_metadata(signed, trust)

    def test_duplicate_key_id_fails(self):
        trust = TrustStore()
        from updates.signing import export_public_key_pem
        pem = export_public_key_pem(self.public, "key1")
        trust.add_key("key1", pem)
        _, other_pub = generate_keypair()
        other_pem = export_public_key_pem(other_pub, "key1")
        with self.assertRaises(TrustError):
            trust.add_key("key1", other_pem)

    def test_malformed_pem_fails(self):
        trust = TrustStore()
        with self.assertRaises(TrustError):
            trust.add_key("key1", "not a pem")


if __name__ == "__main__":
    unittest.main()
