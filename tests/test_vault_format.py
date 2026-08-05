"""Tests for vault envelope format and schema validation."""

from __future__ import annotations

import json
import unittest

from security.vault.format import envelope_from_json, envelope_to_json, make_envelope, parse_envelope
from security.vault.errors import VaultFormatError


TEST_KDF = {"name": "scrypt", "n": 2**10, "r": 8, "p": 1}


class VaultFormatTests(unittest.TestCase):
    def test_valid_schema(self):
        plaintext = b"hello vault"
        env = make_envelope(plaintext, "password", TEST_KDF)
        self.assertEqual(env["schema_version"], 1)
        self.assertIn("ciphertext", env)
        self.assertIn("authentication", env)

    def test_unknown_schema_rejected(self):
        with self.assertRaises(VaultFormatError):
            parse_envelope({"schema_version": 999})

    def test_unsupported_cipher_rejected(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["cipher"]["name"] = "DES"
        with self.assertRaises(VaultFormatError):
            parse_envelope(env)

    def test_unsupported_kdf_rejected(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["kdf"]["name"] = "pbkdf2"
        with self.assertRaises(VaultFormatError):
            parse_envelope(env)

    def test_missing_salt_rejected(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        del env["kdf"]["salt"]
        with self.assertRaises(VaultFormatError):
            parse_envelope(env)

    def test_missing_nonce_rejected(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        del env["cipher"]["nonce"]
        with self.assertRaises(VaultFormatError):
            parse_envelope(env)

    def test_malformed_ciphertext_fails_decryption(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["ciphertext"] = "dGFi"
        parsed = parse_envelope(env)
        from security.vault.crypto import derive_key, decrypt
        key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
        with self.assertRaises(Exception):
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"])

    def test_authentication_failure(self):
        from security.vault.crypto import derive_key, decrypt
        env = make_envelope(b"x", "p", TEST_KDF)
        parsed = parse_envelope(env)
        key = derive_key("wrong", parsed["salt"], parsed["kdf_parameters"])
        with self.assertRaises(Exception):
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"])

    def test_unique_salt(self):
        env1 = make_envelope(b"x", "p", TEST_KDF)
        env2 = make_envelope(b"x", "p", TEST_KDF)
        self.assertNotEqual(env1["kdf"]["salt"], env2["kdf"]["salt"])

    def test_unique_nonce(self):
        env1 = make_envelope(b"x", "p", TEST_KDF)
        env2 = make_envelope(b"x", "p", TEST_KDF)
        self.assertNotEqual(env1["cipher"]["nonce"], env2["cipher"]["nonce"])

    def test_no_plaintext_secret_in_file(self):
        env = make_envelope(b"SECRET", "p", TEST_KDF)
        text = envelope_to_json(env)
        self.assertNotIn("SECRET", text)

    def test_no_plaintext_password_verifier(self):
        env = make_envelope(b"x", "password", TEST_KDF)
        text = envelope_to_json(env)
        self.assertNotIn("password", text)

    def test_modified_kdf_name_fails(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["kdf"]["name"] = "other"
        with self.assertRaises((VaultFormatError, Exception)):
            parsed = parse_envelope(env)
            from security.vault.crypto import derive_key, decrypt
            key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], parsed["associated_data"])

    def test_modified_cipher_name_fails(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["cipher"]["name"] = "other"
        with self.assertRaises((VaultFormatError, Exception)):
            parsed = parse_envelope(env)
            from security.vault.crypto import derive_key, decrypt
            key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], parsed["associated_data"])

    def test_modified_salt_fails(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        # Replace salt with a fresh random one
        import base64, os
        env["kdf"]["salt"] = base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")
        parsed = parse_envelope(env)
        from security.vault.crypto import derive_key, decrypt
        key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
        with self.assertRaises(Exception):
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], parsed["associated_data"])

    def test_modified_metadata_vault_id_not_auth_fails(self):
        env = make_envelope(b"x", "p", TEST_KDF)
        env["metadata"]["vault_id"] = "tampered"
        # vault_id is not in AAD, so this still decrypts; test demonstrates that only security-critical metadata is authenticated.
        parsed = parse_envelope(env)
        from security.vault.crypto import derive_key, decrypt
        key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
        self.assertEqual(decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], parsed["associated_data"]), b"x")


if __name__ == "__main__":
    unittest.main()
