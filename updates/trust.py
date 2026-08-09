"""Trust levels and trust-store helpers.

Canonical production trust-store location:
    updates/trust_store/hive-release.pem

This is the single authoritative PEM trust-store file for Hive OS
production releases. It is stored in the repository and shipped with
the code. All other trust-store paths are development or override paths.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)
from cryptography.exceptions import InvalidSignature

from updates.errors import TrustError

# Single canonical production trust-store file.
TRUST_STORE_PATH: Path = Path("updates/trust_store/hive-release.pem")


class TrustLevel(Enum):
    DEVELOPMENT_GIT = "development_git"
    SIGNED_RELEASE = "signed_release"
    OFFLINE_VERIFIED_BUNDLE = "offline_verified_bundle"
    EMERGENCY_RECOVERY_BUNDLE = "emergency_recovery_bundle"


def _compute_fingerprint(public_key: Ed25519PublicKey) -> str:
    """SHA-256 over canonical raw Ed25519 public key bytes (32 bytes)."""
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _valid_hex_fingerprint(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


@dataclass
class TrustedKey:
    key_id: str
    public_key: Ed25519PublicKey
    role: str = "release"
    status: str = "active"
    revoked_at: str | None = None
    replacement_key_id: str | None = None
    fingerprint: str = ""

    def inspect(self) -> dict[str, Any]:
        fp = self.fingerprint or _compute_fingerprint(self.public_key)
        return {
            "key_id": self.key_id,
            "fingerprint": fp,
            "purpose": self.role,
            "status": self.status,
            "revoked_at": self.revoked_at,
            "replacement_key_id": self.replacement_key_id,
        }


class TrustStore:
    """In-memory trust store backed by a JSON file of PEM public keys."""

    def __init__(self, keys: dict[str, TrustedKey] | None = None):
        self.keys: dict[str, TrustedKey] = keys or {}

    @classmethod
    def from_pem_file(cls, path: Path) -> "TrustStore":
        """Load PEM public keys. Private keys are never accepted here."""
        if not path.exists():
            return cls({})
        if path.is_symlink():
            return cls({})
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return cls({})
        keys: dict[str, TrustedKey] = {}
        entries = raw.split("-----BEGIN PUBLIC KEY-----")
        for idx, entry in enumerate(entries[1:], start=1):
            block = "-----BEGIN PUBLIC KEY-----" + entry
            try:
                pub = load_pem_public_key(block.encode("utf-8"))
            except Exception:
                continue

            key_id = f"key-{len(keys) + 1}"
            fingerprint = ""
            purpose = "release"
            has_key_id_comment = False

            preceding = entries[idx - 1]
            for line in preceding.splitlines():
                line_stripped = line.strip()
                if line_stripped.startswith("# key_id:"):
                    has_key_id_comment = True
                    key_id = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("# fingerprint_sha256:"):
                    fingerprint = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("# purpose:"):
                    purpose = line_stripped.split(":", 1)[1].strip()

            if not isinstance(pub, Ed25519PublicKey):
                if has_key_id_comment:
                    raise TrustError(
                        f"Explicitly declared trusted entry {key_id} is not Ed25519"
                    )
                continue

            if fingerprint and not _valid_hex_fingerprint(fingerprint):
                raise TrustError(f"Malformed fingerprint for key {key_id}")

            computed = _compute_fingerprint(pub)

            if fingerprint and fingerprint.lower() != computed:
                raise TrustError(
                    f"Fingerprint mismatch for key {key_id}: "
                    f"expected {fingerprint}, got {computed}"
                )

            if key_id in keys:
                existing = keys[key_id]
                existing_fp = existing.fingerprint or _compute_fingerprint(existing.public_key)
                if existing_fp != computed:
                    raise TrustError(f"Duplicate key_id {key_id} with different key")
                if fingerprint and existing.fingerprint and existing.fingerprint != fingerprint:
                    raise TrustError(f"Duplicate key_id {key_id} with conflicting fingerprint")
                # Even identical material is a duplicate declaration — fail closed
                raise TrustError(f"Duplicate key_id: {key_id}")

            keys[key_id] = TrustedKey(
                key_id=key_id,
                public_key=pub,
                role=purpose,
                status="active",
                fingerprint=computed if not fingerprint else fingerprint,
            )
        return cls(keys)

    def verify(
        self,
        key_id: str,
        message: bytes,
        signature: bytes,
        expected_purpose: str | None = None,
    ) -> None:
        key = self.keys.get(key_id)
        if key is None:
            raise TrustError(f"Unknown key ID: {key_id}")
        if key.status != "active":
            raise TrustError(f"Key {key_id} has been revoked")
        if expected_purpose and key.role != expected_purpose:
            raise TrustError(
                f"Key {key_id} purpose {key.role} does not match expected {expected_purpose}"
            )
        try:
            key.public_key.verify(signature, message)
        except InvalidSignature as e:
            raise TrustError(f"Signature mismatch for key {key_id}") from e

    def add_key(
        self,
        key_id: str,
        pem_text: str,
        fingerprint: str = "",
        purpose: str = "release",
    ) -> None:
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

        computed = _compute_fingerprint(pub)
        if fingerprint and not _valid_hex_fingerprint(fingerprint):
            raise TrustError(f"Malformed fingerprint for key {key_id}")
        if fingerprint and fingerprint.lower() != computed:
            raise TrustError(
                f"Fingerprint mismatch for key {key_id}: "
                f"expected {fingerprint}, got {computed}"
            )

        self.keys[key_id] = TrustedKey(
            key_id=key_id,
            public_key=pub,
            role=purpose,
            status="active",
            fingerprint=computed if not fingerprint else fingerprint,
        )

    def revoke_key(self, key_id: str, replacement_key_id: str | None = None) -> None:
        if key_id not in self.keys:
            raise TrustError(f"Cannot revoke unknown key: {key_id}")
        from datetime import datetime, timezone
        self.keys[key_id].status = "revoked"
        self.keys[key_id].revoked_at = datetime.now(timezone.utc).isoformat()
        if replacement_key_id:
            self.keys[key_id].replacement_key_id = replacement_key_id
