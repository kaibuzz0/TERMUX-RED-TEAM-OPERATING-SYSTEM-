"""Cryptographic primitives for the Hive vault.

Uses only the `cryptography` library's AEAD API and standard-library scrypt.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


# Domain-separation labels for HKDF. Each distinct key or purpose gets its own label.
HKDF_INFO_ENCRYPTION_V1 = b"hive-vault-encryption-v1"


class CryptoError(Exception):
    """Cryptographic operation failure."""


def _build_associated_data(schema_version: int, kdf_name: str, cipher_name: str) -> bytes:
    """Build authenticated associated data from security-critical envelope metadata.

    This binds the ciphertext to the envelope's algorithm choices and schema version,
    so a down-grade or algorithm-swap attack causes decryption to fail.
    """
    return json.dumps(
        {"schema_version": schema_version, "kdf": kdf_name, "cipher": cipher_name},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def derive_key(master_password: str, salt: bytes, parameters: dict[str, Any]) -> bytes:
    """Derive the vault encryption key from *master_password*.

    Key hierarchy:
      1. master_material = scrypt(password, salt, scrypt_params)   [memory-hard KDF]
      2. encryption_key  = HKDF-SHA256(master_material, info=HKDF_INFO_ENCRYPTION_V1)

    scrypt provides the password-hardening and salt-bound uniqueness.
    HKDF provides domain separation so the raw scrypt output is never used directly
    as an AES key and so future subkeys (metadata, backup, etc.) can be derived from
    the same master_material with distinct info labels without cross-use.
    """

    if len(salt) < 16:
        raise CryptoError("Salt too short")

    n = int(parameters.get("n", 2**14))
    r = int(parameters.get("r", 8))
    p = int(parameters.get("p", 1))

    if n < 2 or (n & (n - 1)) != 0:
        raise CryptoError("scrypt parameter n must be a power of two")

    expected_mem = 128 * n * r * p
    if expected_mem > 1024 * 1024 * 1024:
        raise CryptoError("scrypt parameters exceed safety memory bound")

    # OpenSSL/scrypt may need more working memory than the theoretical minimum.
    max_mem = max(64 * 1024 * 1024, expected_mem * 4)

    try:
        scrypt_key = hashlib.scrypt(
            master_password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=max_mem,
            dklen=32,
        )
    except Exception as e:
        raise CryptoError(f"scrypt derivation failed: {e}") from e

    # HKDF-SHA256 separates the AES key from the raw scrypt output and domain-labels it.
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=HKDF_INFO_ENCRYPTION_V1,
    )
    return hkdf.derive(scrypt_key)


def encrypt(key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes) -> tuple[bytes, bytes]:
    """AEAD encrypt with AES-256-GCM; return (ciphertext, tag)."""

    if len(key) != 32:
        raise CryptoError("AES-256-GCM requires a 32-byte key")
    if len(nonce) != 12:
        raise CryptoError("AES-256-GCM requires a 12-byte nonce")

    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    # AESGCM appends 16-byte tag
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    return ciphertext, tag


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, associated_data: bytes) -> bytes:
    """AEAD decrypt with AES-256-GCM; raises InvalidTag on authentication failure."""

    if len(key) != 32:
        raise CryptoError("AES-256-GCM requires a 32-byte key")
    if len(nonce) != 12:
        raise CryptoError("AES-256-GCM requires a 12-byte nonce")
    if len(tag) != 16:
        raise CryptoError("AES-256-GCM tag must be 16 bytes")

    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext + tag, associated_data)
    except Exception as e:
        raise CryptoError(f"Decryption failed: {e}") from e
