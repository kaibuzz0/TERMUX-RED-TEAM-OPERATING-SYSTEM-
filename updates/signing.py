"""Ed25519 signing helpers.

Private keys are only used by the release tooling, never by the runtime.
The runtime only verifies with public keys from the trust store.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from updates.metadata import canonical_json
from updates.trust import TrustStore, _compute_fingerprint
from updates.errors import TrustError


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def sign_metadata(metadata: dict[str, Any], private_key: Ed25519PrivateKey, key_id: str) -> dict[str, Any]:
    signed = dict(metadata)
    signed["signing"] = {"algorithm": "Ed25519", "key_id": key_id, "signature": ""}
    signed["manifest_digest"] = signed.get("manifest_digest", "")
    message = canonical_json(signed).encode("utf-8")
    signature = private_key.sign(message)
    signed["signing"]["signature"] = base64.urlsafe_b64encode(signature).decode("ascii")
    return signed


def verify_metadata(
    metadata: dict[str, Any],
    trust_store: TrustStore,
    expected_purpose: str | None = None,
) -> None:
    sig_block = metadata.get("signing", {})
    algorithm = sig_block.get("algorithm")
    key_id = sig_block.get("key_id")
    signature_b64 = sig_block.get("signature", "")
    if algorithm != "Ed25519":
        raise TrustError(f"Unsupported signing algorithm: {algorithm}")
    if not key_id or not signature_b64:
        raise TrustError("Missing signing metadata")
    signed = dict(metadata)
    signed["signing"] = {"algorithm": algorithm, "key_id": key_id, "signature": ""}
    message = canonical_json(signed).encode("utf-8")
    signature = base64.urlsafe_b64decode(signature_b64.encode("ascii"))
    trust_store.verify(key_id, message, signature, expected_purpose=expected_purpose)


def export_public_key_pem(public_key: Ed25519PublicKey, key_id: str, purpose: str = "release") -> str:
    pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    fp = _compute_fingerprint(public_key)
    return f"# key_id: {key_id}\n# fingerprint_sha256: {fp}\n# purpose: {purpose}\n{pem}"


def export_private_key_pem(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode("utf-8")


def load_private_key_pem(text: str) -> Ed25519PrivateKey:
    """Load an Ed25519 private key from PEM text.

    Supports:
    - PKCS#8 PEM (unencrypted or encrypted) via load_pem_private_key()
    - OpenSSH private key format via load_ssh_private_key()

    Production keys MUST be encrypted at rest.
    """
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key,
        load_ssh_private_key,
    )
    data = text.encode("utf-8")
    # Try PKCS#8 PEM first
    try:
        key = load_pem_private_key(data, password=None)
    except Exception:
        # OpenSSH format as alternative
        key = load_ssh_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    return key
