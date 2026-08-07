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


def load_private_key(path: Path) -> Ed25519PrivateKey:
    """Load a PEM Ed25519 private key from an external path.

    Private keys are never committed; this loader is for offline signing only.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    pem = path.read_bytes()
    key = load_pem_private_key(pem, password=None)
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


def verify_release_metadata(metadata: Dict[str, Any], trust_store: TrustStore) -> None:
    """Verify a release metadata signature against the trust store."""
    verify_metadata(metadata, trust_store)
