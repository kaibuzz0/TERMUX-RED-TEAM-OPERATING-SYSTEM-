"""Vault backend: encrypt/decrypt secrets."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from security.vault.crypto import derive_key, decrypt, encrypt
from security.vault.format import envelope_from_json, envelope_to_json, make_envelope, parse_envelope
from security.vault.storage import VaultStorage
from security.vault.errors import VaultError, VaultExistsError, VaultLockedError, VaultSafetyError
from security.vault.redaction import redact


TEST_KDF_PARAMETERS = {"name": "scrypt", "n": 2**10, "r": 8, "p": 1}


@dataclass
class SecretRecord:
    name: str
    secret_type: str = "opaque"
    scope: str = "OPERATOR_ONLY"
    allowed_consumer: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    expires_at: str = ""
    rotation_state: str = "current"
    value: bytes = field(default=b"", repr=False)

    def to_dict(self, include_value: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "secret_type": self.secret_type,
            "scope": self.scope,
            "allowed_consumer": self.allowed_consumer,
            "created_at": self.created_at,
            "updated_at": self.updated_at or self.created_at,
            "expires_at": self.expires_at,
            "rotation_state": self.rotation_state,
        }
        if include_value:
            d["value"] = self.value.decode("utf-8")
        return d


class Vault:
    """Encrypted vault for Hive operator credentials and scoped secrets."""

    VAULT_DATA_SCHEMA = 1

    def __init__(self, vault_dir: Path | None = None):
        home = Path(os.environ.get("HOME", "/tmp"))
        self.vault_dir = vault_dir or (home / ".hive" / "vault")
        self.storage = VaultStorage(self.vault_dir)
        self._key: bytes | None = None
        self._secrets: dict[str, SecretRecord] = {}
        self._metadata: dict[str, Any] = {}
        self._kdf_parameters: dict[str, Any] = TEST_KDF_PARAMETERS

    def locked(self) -> bool:
        return self._key is None

    def exists(self) -> bool:
        return self.storage.exists()

    def init(self, master_password: str, kdf_parameters: dict[str, Any] | None = None) -> None:
        """Create a new empty vault."""
        if self.storage.exists():
            raise VaultExistsError("Vault already exists")
        params = kdf_parameters or self._kdf_parameters
        plaintext = json.dumps({"schema": self.VAULT_DATA_SCHEMA, "secrets": {}}).encode("utf-8")
        envelope = make_envelope(plaintext, master_password, params)
        self.storage.write(envelope_to_json(envelope), overwrite=False)

    def unlock(self, master_password: str) -> None:
        """Unlock the vault with the master password."""
        if not self.storage.exists():
            raise VaultError("Vault does not exist")
        text = self.storage.read()
        envelope = envelope_from_json(text)
        parsed = parse_envelope(envelope)

        self._kdf_parameters = parsed["kdf_parameters"]
        key = derive_key(master_password, parsed["salt"], parsed["kdf_parameters"])
        plaintext = decrypt(key, parsed["nonce"], parsed["ciphertext"], parsed["tag"], parsed["associated_data"])
        data = json.loads(plaintext.decode("utf-8"))
        if data.get("schema") != self.VAULT_DATA_SCHEMA:
            raise VaultError("Unknown vault data schema")

        self._key = key
        self._metadata = envelope.get("metadata", {})
        self._secrets = {}
        for name, record in data.get("secrets", {}).items():
            self._secrets[name] = SecretRecord(
                name=record["name"],
                secret_type=record.get("secret_type", "opaque"),
                scope=record.get("scope", "OPERATOR_ONLY"),
                allowed_consumer=record.get("allowed_consumer", ""),
                created_at=record.get("created_at", ""),
                updated_at=record.get("updated_at", ""),
                expires_at=record.get("expires_at", ""),
                rotation_state=record.get("rotation_state", "current"),
                value=record.get("value", "").encode("utf-8"),
            )

    def lock(self) -> None:
        """Lock the vault, clearing the derived key from memory."""
        self._key = None
        self._secrets = {}
        self._metadata = {}

    def set(
        self,
        name: str,
        value: str | bytes,
        secret_type: str = "opaque",
        scope: str = "OPERATOR_ONLY",
        allowed_consumer: str = "",
    ) -> None:
        if self.locked():
            raise VaultLockedError("Vault is locked")
        if not isinstance(value, (str, bytes)):
            raise VaultSafetyError("Secret value must be str or bytes")
        encoded = value.encode("utf-8") if isinstance(value, str) else value
        now = datetime.now(timezone.utc).isoformat()
        existing = self._secrets.get(name)
        self._secrets[name] = SecretRecord(
            name=name,
            secret_type=secret_type,
            scope=scope,
            allowed_consumer=allowed_consumer,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            value=encoded,
        )

    def get(self, name: str) -> bytes:
        if self.locked():
            raise VaultLockedError("Vault is locked")
        record = self._secrets.get(name)
        if record is None:
            raise VaultError(f"Secret not found: {name}")
        return record.value

    def list(self, include_values: bool = False) -> list[dict[str, Any]]:
        if self.locked():
            raise VaultLockedError("Vault is locked")
        records = []
        for record in self._secrets.values():
            d = record.to_dict(include_value=include_values)
            if not include_values:
                d.pop("value", None)
            records.append(redact(d))
        return records

    def remove(self, name: str) -> None:
        if self.locked():
            raise VaultLockedError("Vault is locked")
        if name not in self._secrets:
            raise VaultError(f"Secret not found: {name}")
        del self._secrets[name]

    def save(self, master_password: str) -> None:
        """Persist current secrets by re-encrypting the vault with *master_password*."""
        if not self.storage.exists():
            raise VaultError("Vault does not exist")

        data = {
            "schema": self.VAULT_DATA_SCHEMA,
            "secrets": {
                name: {
                    **record.to_dict(include_value=True),
                    "value": record.value.decode("utf-8"),
                }
                for name, record in self._secrets.items()
            },
        }
        plaintext = json.dumps(data).encode("utf-8")

        text = self.storage.read()
        envelope = envelope_from_json(text)
        parsed = parse_envelope(envelope)
        kdf_params = {
            "name": "scrypt",
            "n": parsed["kdf_parameters"]["n"],
            "r": parsed["kdf_parameters"]["r"],
            "p": parsed["kdf_parameters"]["p"],
        }
        new_envelope = make_envelope(plaintext, master_password, kdf_params)
        self.storage.write(envelope_to_json(new_envelope), overwrite=True)

    def status(self) -> dict[str, Any]:
        return {
            "exists": self.storage.exists(),
            "locked": self.locked(),
            "vault_dir": str(self.vault_dir),
            "secret_count": len(self._secrets) if not self.locked() else None,
            "metadata": redact(self._metadata),
        }
