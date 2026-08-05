"""Strict task manifest schema validation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from hive_broker.errors import ManifestError


MAX_MANIFEST_BYTES = 64 * 1024
MIN_TIMEOUT = 1
MAX_TIMEOUT = 3600
MAX_TASK_ID_LEN = 128
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def validate_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ManifestError("Manifest must be a JSON object")
    schema_version = raw.get("schema_version")
    if schema_version != 1:
        raise ManifestError(f"Unsupported manifest schema version: {schema_version}")

    _require_str(raw, "task_id")
    _require_str(raw, "requestor")
    _require_str(raw, "intent")

    task_id = raw["task_id"]
    if not task_id or len(task_id) > MAX_TASK_ID_LEN or not SAFE_ID_RE.match(task_id):
        raise ManifestError(f"Invalid task_id: {task_id!r}")

    required_capabilities = _list_of_str(raw, "required_capabilities", allow_empty=False)
    allowed_actions = _list_of_str(raw, "allowed_actions", allow_empty=False)

    # Target lists
    target_services = _list_of_str(raw, "target_services", allow_empty=True)
    target_paths = _list_of_str(raw, "target_paths", allow_empty=True)

    read_only = raw.get("read_only")
    if not isinstance(read_only, bool):
        raise ManifestError("read_only must be a boolean")

    timeout = raw.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
        raise ManifestError(f"timeout_seconds must be an integer between {MIN_TIMEOUT} and {MAX_TIMEOUT}")

    audit_level = raw.get("audit_level", "normal")
    if audit_level not in {"normal", "verbose", "quiet"}:
        raise ManifestError(f"Unknown audit_level: {audit_level}")

    # Reject unknown top-level fields
    allowed_fields = {
        "schema_version", "task_id", "requestor", "intent",
        "required_capabilities", "allowed_actions", "target_services",
        "target_paths", "read_only", "timeout_seconds", "audit_level",
        "allowed_since_commit",
    }
    unknown = set(raw.keys()) - allowed_fields
    if unknown:
        raise ManifestError(f"Unknown manifest fields: {sorted(unknown)}")

    # Allowed since commit is optional string
    if "allowed_since_commit" in raw and not isinstance(raw["allowed_since_commit"], str):
        raise ManifestError("allowed_since_commit must be a string")

    # Check duplicates
    if len(required_capabilities) != len(set(required_capabilities)):
        raise ManifestError("Duplicate capability in required_capabilities")
    if len(allowed_actions) != len(set(allowed_actions)):
        raise ManifestError("Duplicate action in allowed_actions")

    return {
        "schema_version": 1,
        "task_id": task_id,
        "requestor": raw["requestor"],
        "intent": raw["intent"],
        "required_capabilities": required_capabilities,
        "allowed_actions": allowed_actions,
        "target_services": target_services,
        "target_paths": target_paths,
        "read_only": read_only,
        "timeout_seconds": timeout,
        "audit_level": audit_level,
        "allowed_since_commit": raw.get("allowed_since_commit"),
    }


def _require_str(raw: dict[str, Any], key: str) -> None:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{key} must be a non-empty string")


def _list_of_str(raw: dict[str, Any], key: str, allow_empty: bool) -> list[str]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ManifestError(f"{key} must be a list of strings")
    if not allow_empty and len(value) == 0:
        raise ManifestError(f"{key} must not be empty")
    return list(value)


def manifest_digest(manifest: dict[str, Any]) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
