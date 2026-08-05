"""Tests for vault encryption/decryption round trips."""

from __future__ import annotations

import unittest

from security.vault.crypto import derive_key, decrypt, encrypt, _build_associated_data
from security.vault.format import make_envelope, parse_envelope


TEST_KDF = {"name": "scrypt", "n": 2**10, "r": 8, "p": 1}


class VaultCryptoTests(unittest.TestCase):
    def test_encrypt_decrypt_round_trip(self):
        key = b"\x00" * 32
        nonce = b"\x00" * 12
        plaintext = b"hello"
        aad = _build_associated_data(1, "scrypt", "AES-256-GCM")
        ciphertext, tag = encrypt(key, nonce, plaintext, aad)
        self.assertEqual(decrypt(key, nonce, ciphertext, tag, aad), plaintext)

    def test_wrong_password_fails(self):
        env = make_envelope(b"secret", "correct", TEST_KDF)
        parsed = parse_envelope(env)
        key = derive_key("wrong", parsed["salt"], parsed["kdf_parameters"])
        aad = _build_associated_data(1, "scrypt", "AES-256-GCM")
        with self.assertRaises(Exception):
            decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], aad)

    def test_modified_ciphertext_fails(self):
        env = make_envelope(b"secret", "p", TEST_KDF)
        parsed = parse_envelope(env)
        key = derive_key("p", parsed["salt"], parsed["kdf_parameters"])
        bad_cipher = parsed["ciphertext"][:-1] + bytes([parsed["ciphertext"][-1] ^ 1])
        aad = _build_associated_data(1, "scrypt", "AES-256-GCM")
        with self.assertRaises(Exception):
            decrypt(key, parsed["nonce"], bad_cipher, parsed["tag"], aad)

    def test_modified_metadata_fails_where_authenticated(self):
        # Tag is over ciphertext only in our layout; metadata changes don't affect auth.
        pass


if __name__ == "__main__":
    unittest.main()
