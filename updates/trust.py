"""Trust levels and trust-store helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

from updates.errors import TrustError


class TrustLevel(Enum):
    DEVELOPMENT_GIT = "development_git"
    SIGNED_RELEASE = "signed_release"
    OFFLINE_VERIFIED_BUNDLE = "offline_verified_bundle"
    EMERGENCY_RECOVERY_BUNDLE = "emergency_recovery_bundle"


@dataclass
class TrustedKey:
    key_id: str
    public_key: Ed25519PublicKey
    role: str = "release"
    revoked: bool = False


class TrustStore:
    """In-memory trust store backed by a JSON file of PEM public keys."""

    def __init__(self, keys: dict[str, TrustedKey] | None = None):
        self.keys: dict[str, TrustedKey] = keys or {}

    @classmethod
    def from_pem_file(cls, path: Path) -> "TrustStore":
        """Load PEM public keys. Private keys are never accepted here."""
        if not path.exists():
            return cls({})
        raw = path.read_text(encoding="utf-8")
        keys: dict[str, TrustedKey] = {}
        # Accept concatenated PEM blocks separated by key_id comments
        entries = raw.split("-----BEGIN PUBLIC KEY-----")
        for entry in entries[1:]:
            block = "-----BEGIN PUBLIC KEY-----" + entry
            try:
                pub = load_pem_public_key(block.encode("utf-8"))
                if not isinstance(pub, Ed25519PublicKey):
                    continue
                # key_id from preceding comment line if present
                key_id = f"key-{len(keys) + 1}"
                preceding = entries[entries.index("-----BEGIN PUBLIC KEY-----" + entry) - 1]
                for line in preceding.splitlines():
                    if line.strip().startswith("# key_id:"):
                        key_id = line.split(":", 1)[1].strip()
                keys[key_id] = TrustedKey(key_id=key_id, public_key=pub)
            except Exception:
                continue
        return cls(keys)

    def verify(self, key_id: str, message: bytes, signature: bytes) -> None:
        key = self.keys.get(key_id)
        if key is None:
            raise TrustError(f"Unknown key ID: {key_id}")
        if key.revoked:
            raise TrustError(f"Key {key_id} has been revoked")
        try:
            key.public_key.verify(signature, message)
        except InvalidSignature as e:
            raise TrustError(f"Signature mismatch for key {key_id}") from e

    def add_key(self, key_id: str, pem_text: str) -> None:
        if not key_id:
            raise TrustError("key_id must be non-empty")
        if key_id in self.keys:
            raise TrustError(f"Duplicate key_id: {key_id}")
        try:
            pub = load_pem_public_key(pem_text.encode("utf-8"))
        except Exception as e:
            raise TrustError(f"Malformed PEM for key {key_id}: {e}") from e
        if not isinstance(pub, Ed25519PublicKey):
            raise TrustError("Only Ed25519 public keys are supported")
        self.keys[key_id] = TrustedKey(key_id=key_id, public_key=pub)

    def revoke_key(self, key_id: str) -> None:
        if key_id not in self.keys:
            raise TrustError(f"Cannot revoke unknown key: {key_id}")
        self.keys[key_id].revoked = True
