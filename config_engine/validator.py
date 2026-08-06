"""Additional cross-field and security validation for resolved configurations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from config_engine.errors import ConfigValidationError


PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.(?:[/\\]|$)")


def validate_subsystem_config(name: str, config: dict[str, Any], runtime: dict[str, Any] | None = None) -> list[dict]:
    """Run subsystem-specific validation beyond schema checks."""
    errors: list[dict] = []
    runtime = runtime or {}

    if name == "services":
        errors.extend(_validate_services(config))
    elif name == "updates":
        errors.extend(_validate_updates(config))
    elif name == "broker":
        errors.extend(_validate_broker(config))
    elif name == "runtime":
        errors.extend(_validate_runtime(config))

    # Path containment for all path-like fields
    for key, value in config.items():
        candidates: list[str] = []
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [v for v in value if isinstance(v, str)]
        for candidate in candidates:
            if PATH_TRAVERSAL_PATTERN.search(candidate):
                errors.append({"field": key, "message": f"Path traversal pattern rejected: {candidate!r}"})
                break

    return errors


def _validate_services(config: dict[str, Any]) -> list[dict]:
    errors = []
    backoff_min = config.get("backoff_base_seconds", 1)
    backoff_max = config.get("backoff_max_seconds", 60)
    if backoff_min > backoff_max:
        errors.append({
            "field": "backoff",
            "message": f"backoff_base_seconds ({backoff_min}) exceeds backoff_max_seconds ({backoff_max})",
        })
    return errors


def _validate_updates(config: dict[str, Any]) -> list[dict]:
    errors = []
    if config.get("signature_required") and not config.get("anti_rollback"):
        errors.append({
            "field": "anti_rollback",
            "message": "signature_required should be paired with anti_rollback for safe updates",
        })
    return errors


def _validate_broker(config: dict[str, Any]) -> list[dict]:
    errors = []
    # Production profile should not enable mutating actions by default.
    if config.get("policy_profile") == "production" and config.get("mutating_actions_enabled"):
        errors.append({
            "field": "mutating_actions_enabled",
            "message": "production policy profile should not enable mutating actions",
        })
    return errors


def _validate_runtime(config: dict[str, Any]) -> list[dict]:
    errors = []
    log_level = config.get("log_level")
    if log_level and log_level not in {"debug", "info", "warning", "error"}:
        errors.append({"field": "log_level", "message": f"Invalid log level: {log_level}"})
    return errors


def validate_path_containment(path: Path, root: Path, field: str = "path") -> None:
    """Validate that a resolved path stays within an expected root."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        raise ConfigValidationError(f"{field} escapes container: {path}")


def validate_no_duplicate_keys(mapping: dict[str, Any], context: str = "") -> None:
    """JSON parsers already reject duplicate keys; this is an explicit defensive check."""
    seen: set[str] = set()
    for key in mapping:
        if key in seen:
            raise ConfigValidationError(f"Duplicate key detected{f' in {context}' if context else ''}: {key!r}")
        seen.add(key)
