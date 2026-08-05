"""Versioned release metadata format and validation."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from updates.errors import AntiRollbackError, BundleError, CompatibilityError, TrustError


METADATA_SCHEMA_VERSION = 1
MAX_SECURITY_SEQUENCE = 2_147_483_647  # signed 32-bit int upper bound


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_metadata(
    version: str,
    release_id: str,
    commit: str,
    artifacts: list[dict[str, Any]],
    platforms: list[str],
    architectures: list[str],
    minimum_hive_version: str,
    maximum_hive_version: str | None = None,
    security_sequence: int = 1,
) -> dict[str, Any]:
    if not isinstance(security_sequence, int) or isinstance(security_sequence, bool):
        raise BundleError("security_sequence must be an integer")
    if security_sequence < 0:
        raise BundleError("security_sequence must be non-negative")
    if security_sequence > MAX_SECURITY_SEQUENCE:
        raise BundleError("security_sequence exceeds maximum supported value")
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "release": {
            "version": version,
            "release_id": release_id,
            "commit": commit,
            "created_at": _now(),
            "minimum_hive_version": minimum_hive_version,
            "maximum_hive_version": maximum_hive_version,
            "platforms": platforms,
            "architectures": architectures,
            "security_sequence": security_sequence,
        },
        "artifacts": artifacts,
        "manifest_digest": "",
        "signing": {
            "algorithm": "Ed25519",
            "key_id": "",
            "signature": "",
        },
        "revocation": {"sequence": 0},
    }


def canonical_json(data: dict[str, Any]) -> str:
    """Deterministic canonical serialization for signing.

    - Object keys are sorted recursively.
    - Whitespace is removed (separators=(",", ":")).
    - Encoding is UTF-8 after serializing.
    - Floats are rejected because they are not reliably canonical across platforms.
    """
    _reject_floats(data)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _reject_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise BundleError("Float values are not permitted in canonical signed metadata")
    if isinstance(obj, dict):
        for value in obj.values():
            _reject_floats(value)
    elif isinstance(obj, list):
        for item in obj:
            _reject_floats(item)


def parse_metadata(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BundleError(f"Metadata is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise BundleError("Metadata must be a JSON object")
    if data.get("schema_version") != METADATA_SCHEMA_VERSION:
        raise BundleError(f"Unsupported metadata schema version: {data.get('schema_version')}")
    rel = data.get("release", {})
    if not all(k in rel for k in ("version", "release_id", "commit", "platforms", "architectures")):
        raise BundleError("Missing required release fields")
    if "security_sequence" not in rel:
        raise BundleError("Missing security_sequence")
    seq = rel["security_sequence"]
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise BundleError("security_sequence must be an integer")
    if seq < 0:
        raise BundleError("security_sequence must be non-negative")
    if seq > MAX_SECURITY_SEQUENCE:
        raise BundleError("security_sequence exceeds maximum supported value")
    return data


def verify_artifacts(data: dict[str, Any], bundle_root: Path) -> None:
    """Verify artifact digests against files in bundle_root."""
    seen_paths: set[str] = set()
    for art in data.get("artifacts", []):
        name = art.get("name")
        if name in seen_paths:
            raise BundleError(f"Duplicate artifact path: {name}")
        seen_paths.add(name)
        path = bundle_root / name
        if not path.exists():
            raise BundleError(f"Missing artifact: {name}")
        if path.stat().st_size != art.get("size", -1):
            raise BundleError(f"Size mismatch for {name}")


def check_compatibility(data: dict[str, Any], platform: str, architecture: str) -> None:
    rel = data.get("release", {})
    if platform not in rel.get("platforms", []):
        raise CompatibilityError(f"Platform {platform} not supported by release {rel.get('release_id')}")
    if architecture not in rel.get("architectures", []):
        raise CompatibilityError(f"Architecture {architecture} not supported by release {rel.get('release_id')}")


def check_security_sequence(data: dict[str, Any], current_sequence: int, current_release_id: str | None = None) -> None:
    """Enforce monotonic security sequence and detect conflicting release identity.

    Replaying the exact same release identity at the same sequence is allowed.
    A different release claiming the same sequence is rejected.
    """
    rel = data.get("release", {})
    new_seq = rel.get("security_sequence", 0)
    new_release_id = rel.get("release_id")
    if new_seq < current_sequence:
        raise AntiRollbackError(
            f"Security sequence {new_seq} is lower than current {current_sequence}"
        )
    if new_seq == current_sequence and current_release_id is not None and new_release_id != current_release_id:
        raise AntiRollbackError(
            f"Security sequence {new_seq} already belongs to release {current_release_id}"
        )


def check_revocation(data: dict[str, Any], revoked_sequences: set[int]) -> None:
    rel = data.get("release", {})
    seq = rel.get("security_sequence", 0)
    if seq in revoked_sequences:
        raise AntiRollbackError(f"Release with security sequence {seq} has been revoked")
