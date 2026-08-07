"""Plugin signature metadata trust model.

Milestone 16 does not require production signing infrastructure. Trust states
are metadata-only and policy may deny unsigned plugins in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class TrustState(str, Enum):
    UNSIGNED = "UNSIGNED"
    SIGNED_UNTRUSTED = "SIGNED_UNTRUSTED"
    SIGNED_TRUSTED = "SIGNED_TRUSTED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class SignatureMetadata:
    trust_state: TrustState
    publisher_id: str | None = None
    signature_blob: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trust_state": self.trust_state.value,
            "publisher_id": self.publisher_id,
            "signature_blob": "[redacted]" if self.signature_blob else None,
        }


def classify_signature(manifest: Dict[str, Any]) -> SignatureMetadata:
    """Classify signature section of a manifest.

    Real Ed25519 verification is deferred until signing infrastructure is ready.
    """
    sig = manifest.get("signature")
    if not sig:
        return SignatureMetadata(trust_state=TrustState.UNSIGNED)
    publisher_id = sig.get("publisher_id")
    signature_blob = sig.get("signature_blob")
    if not publisher_id or not signature_blob:
        return SignatureMetadata(trust_state=TrustState.INVALID_SIGNATURE)
    # In Milestone 16 we do not validate against a trust store.
    return SignatureMetadata(
        trust_state=TrustState.SIGNED_UNTRUSTED,
        publisher_id=publisher_id,
        signature_blob=signature_blob,
    )
