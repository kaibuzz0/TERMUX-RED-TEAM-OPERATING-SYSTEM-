"""Versioned vault envelope format."""

from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from security.vault.crypto import _build_associated_data
from security.vault.errors import VaultFormatError


SUPPORTED_SCHEMA_VERSIONS = {1}
SUPPORTED_CIPHERS = {"AES-256-GCM"}
SUPPORTED_KDFS = {"scrypt"}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text.encode("ascii"))
    except Exception as e:
        raise VaultFormatError(f"Invalid base64 field: {e}")


def make_envelope(
    plaintext: bytes,
    master_password: str,
    kdf_parameters: dict[str, Any],
) -> dict[str, Any]:
    """Create a versioned vault envelope from plaintext bytes."""

    if kdf_parameters.get("name") != "scrypt":
        raise VaultFormatError("Unsupported KDF")

    salt = os.urandom(16)
    nonce = os.urandom(12)
    vault_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    from security.vault.crypto import derive_key, encrypt, _build_associated_data

    key = derive_key(master_password, salt, kdf_parameters)
    associated_data = _build_associated_data(1, kdf_parameters["name"], "AES-256-GCM")
    ciphertext, tag = encrypt(key, nonce, plaintext, associated_data)

    return {
        "schema_version": 1,
        "kdf": {
            "name": "scrypt",
            "salt": _b64(salt),
            "parameters": {
                "n": int(kdf_parameters["n"]),
                "r": int(kdf_parameters["r"]),
                "p": int(kdf_parameters["p"]),
            },
        },
        "cipher": {
            "name": "AES-256-GCM",
            "nonce": _b64(nonce),
        },
        "metadata": {
            "vault_id": vault_id,
            "created_at": now,
            "updated_at": now,
        },
        "ciphertext": _b64(ciphertext),
        "authentication": _b64(tag),
    }


def parse_envelope(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and parse a vault envelope; return decoded material without decrypting."""

    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise VaultFormatError(f"Unsupported vault schema version: {schema_version}")

    kdf = data.get("kdf")
    if not isinstance(kdf, dict):
        raise VaultFormatError("Missing KDF section")
    if kdf.get("name") not in SUPPORTED_KDFS:
        raise VaultFormatError(f"Unsupported KDF: {kdf.get('name')}")
    if "salt" not in kdf or "parameters" not in kdf:
        raise VaultFormatError("Missing KDF salt or parameters")

    cipher = data.get("cipher")
    if not isinstance(cipher, dict):
        raise VaultFormatError("Missing cipher section")
    if cipher.get("name") not in SUPPORTED_CIPHERS:
        raise VaultFormatError(f"Unsupported cipher: {cipher.get('name')}")
    if "nonce" not in cipher:
        raise VaultFormatError("Missing cipher nonce")

    ciphertext = data.get("ciphertext")
    auth = data.get("authentication")
    if not ciphertext or not auth:
        raise VaultFormatError("Missing ciphertext or authentication")

    return {
        "schema_version": schema_version,
        "salt": _unb64(kdf["salt"]),
        "kdf_parameters": kdf["parameters"],
        "nonce": _unb64(cipher["nonce"]),
        "ciphertext": _unb64(ciphertext),
        "tag": _unb64(auth),
        "metadata": data.get("metadata", {}),
        "associated_data": _build_associated_data(
            schema_version,
            kdf.get("name"),
            cipher.get("name"),
        ),
    }


def envelope_to_json(envelope: dict[str, Any]) -> str:
    return json.dumps(envelope, indent=2, sort_keys=True)


def envelope_from_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise VaultFormatError(f"Vault is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise VaultFormatError("Vault envelope must be a JSON object")
    return data
