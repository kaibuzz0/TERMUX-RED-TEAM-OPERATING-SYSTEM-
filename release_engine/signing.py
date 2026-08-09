"""Release signing adapter.

Wraps updates.signing so release_engine does not duplicate Ed25519 logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from updates.signing import generate_keypair, sign_metadata, verify_metadata
from updates.trust import TrustStore


def load_private_key(path: Path, password: bytes | None = None) -> Ed25519PrivateKey:
    """Load an Ed25519 private key from file.

    Supports:
    - PKCS#8 PEM (unencrypted or encrypted) via load_pem_private_key()
    - OpenSSH private key format via load_ssh_private_key()

    Private keys are never committed; this loader is for offline signing only.
    The password is never logged, returned, or persisted.
    """
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key,
        load_ssh_private_key,
    )
    pem = path.read_bytes()
    try:
        key = load_pem_private_key(pem, password=password)
    except Exception:
        key = load_ssh_private_key(pem, password=password)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    return key


def sign_release_metadata(
    metadata: Dict[str, Any],
    private_key: Ed25519PrivateKey,
    key_id: str,
    manifest_digest: str,
) -> Dict[str, Any]:
    """Sign release metadata covering the manifest digest."""
    metadata = dict(metadata)
    metadata["manifest_digest"] = manifest_digest
    return sign_metadata(metadata, private_key, key_id)


def verify_release_metadata(
    metadata: Dict[str, Any],
    trust_store: TrustStore,
    expected_purpose: str | None = "release",
) -> None:
    """Verify a release metadata signature against the trust store."""
    verify_metadata(metadata, trust_store, expected_purpose=expected_purpose)
