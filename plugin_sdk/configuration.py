"""Plugin configuration namespace integration.

Plugins use Config Engine for typed schemas under `plugins.<plugin_id>`.
No direct file parsing, no env override, no global writes, no plaintext secrets.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from plugin_sdk.errors import PluginConfigurationError


def plugin_config_namespace(plugin_id: str) -> str:
    return f"plugins.{plugin_id}"


def validate_config_schema(config: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate plugin config against a JSON-like type schema.

    Schema example: {"fields": {"interval": {"type": "int", "max": 3600}}}
    """
    fields = schema.get("fields", {})
    if not isinstance(fields, dict):
        raise PluginConfigurationError("schema.fields must be a dict")

    for key, spec in fields.items():
        if not isinstance(spec, dict):
            raise PluginConfigurationError(f"schema for {key} must be a dict")
        value = config.get(key)
        if value is None:
            if spec.get("required"):
                raise PluginConfigurationError(f"missing required config: {key}")
            continue
        expected_type = spec.get("type")
        if expected_type == "int" and not isinstance(value, int):
            raise PluginConfigurationError(f"{key} must be int")
        if expected_type == "bool" and not isinstance(value, bool):
            raise PluginConfigurationError(f"{key} must be bool")
        if expected_type == "str" and not isinstance(value, str):
            raise PluginConfigurationError(f"{key} must be str")
        if expected_type == "list" and not isinstance(value, list):
            raise PluginConfigurationError(f"{key} must be list")
        if "max" in spec and isinstance(value, (int, float)) and value > spec["max"]:
            raise PluginConfigurationError(f"{key} exceeds max {spec['max']}")
        if "min" in spec and isinstance(value, (int, float)) and value < spec["min"]:
            raise PluginConfigurationError(f"{key} below min {spec['min']}")

    # Reject unknown config keys only when schema is strict.
    if schema.get("strict"):
        unknown = set(config.keys()) - set(fields.keys())
        if unknown:
            raise PluginConfigurationError(f"unknown config keys: {sorted(unknown)}")


def redact_plugin_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Redact values that look like secrets from plugin config previews."""
    from plugin_sdk.audit import redact_secrets
    return redact_secrets(config)


def digest_plugin_config(config: Dict[str, Any]) -> str:
    """Deterministic digest for plugin config."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
