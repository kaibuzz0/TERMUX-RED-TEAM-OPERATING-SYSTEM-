"""Strict plugin manifest validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from plugin_sdk.errors import PluginBundleError, PluginManifestError
from plugin_sdk.schema import (
    CAPABILITY_PATTERN,
    DEFAULT_AUTO_START,
    DEFAULT_NETWORK_POLICY,
    ENTRYPOINT_PATTERN,
    FORBIDDEN_CAPABILITIES,
    PLUGIN_ID_MAX_LENGTH,
    PLUGIN_ID_PATTERN,
    REQUIRED_MANIFEST_SECTIONS,
    SCHEMA_VERSION,
    SEMVER_PATTERN,
    SUPPORTED_PLUGIN_TYPES,
    WILDCARD_PATTERN,
)


def _reject(value: str, reason: str) -> None:
    raise PluginManifestError(f"{reason}: {value!r}")


def _validate_plugin_id(raw: Any) -> str:
    if not isinstance(raw, str):
        _reject(str(raw), "plugin.id must be a string")
    if len(raw) > PLUGIN_ID_MAX_LENGTH:
        _reject(raw, f"plugin.id exceeds {PLUGIN_ID_MAX_LENGTH} characters")
    if not PLUGIN_ID_PATTERN.match(raw):
        _reject(raw, "plugin.id format invalid")
    return raw


def _validate_semver(raw: Any, field: str) -> str:
    import re
    if not isinstance(raw, str):
        _reject(str(raw), f"{field} must be a string")
    if SEMVER_PATTERN.match(raw):
        return raw
    # Allow major.minor shorthand for SDK/broker versions.
    if re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$", raw):
        return raw
    _reject(raw, f"{field} must be semantic version")


def _validate_entrypoint(raw: Any) -> str:
    if not isinstance(raw, str):
        _reject(str(raw), "plugin.entrypoint must be a string")
    if not ENTRYPOINT_PATTERN.match(raw):
        _reject(raw, "plugin.entrypoint must be dotted.module.callable")
    return raw


def _validate_capabilities(raw: Any, field: str) -> list[str]:
    if not isinstance(raw, list):
        _reject(str(raw), f"{field} must be a list")
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            _reject(str(item), f"{field} entries must be strings")
        if WILDCARD_PATTERN.search(item):
            _reject(item, f"{field} capability contains wildcard")
        if not CAPABILITY_PATTERN.match(item):
            _reject(item, f"{field} capability format invalid")
        if item in FORBIDDEN_CAPABILITIES:
            _reject(item, f"{field} capability forbidden")
        out.append(item)
    return out


def load_manifest(source: str | Path) -> Dict[str, Any]:
    """Load and strictly validate a plugin manifest.

    Unknown schemas, unknown fields, duplicate keys, forbidden capabilities,
    and unsafe defaults all fail closed.
    """
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        text = source

    try:
        # Reject duplicate keys at JSON parse time.
        def _reject_duplicates(pairs: list[tuple[Any, Any]]) -> Dict[Any, Any]:
            result: Dict[Any, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise PluginManifestError(f"duplicate key: {key!r}")
                result[key] = value
            return result

        data = json.loads(text, object_pairs_hook=_reject_duplicates)
    except json.JSONDecodeError as exc:
        raise PluginManifestError(f"manifest JSON invalid: {exc}") from exc

    if not isinstance(data, dict):
        raise PluginManifestError("manifest must be a JSON object")

    # Unknown top-level fields fail closed.
    allowed_top = {"schema_version", "plugin", "compatibility", "permissions", "lifecycle", "dependencies", "signature"}
    unknown = set(data.keys()) - allowed_top
    if unknown:
        raise PluginManifestError(f"unknown top-level fields: {sorted(unknown)}")

    for section in REQUIRED_MANIFEST_SECTIONS:
        if section not in data:
            raise PluginManifestError(f"missing required section: {section}")

    schema_version = data["schema_version"]
    if schema_version != SCHEMA_VERSION:
        raise PluginManifestError(f"unsupported schema_version: {schema_version}")

    plugin = data["plugin"]
    if not isinstance(plugin, dict):
        raise PluginManifestError("plugin must be an object")
    allowed_plugin = {"id", "name", "version", "sdk_version", "entrypoint", "type"}
    unknown_plugin = set(plugin.keys()) - allowed_plugin
    if unknown_plugin:
        raise PluginManifestError(f"unknown plugin fields: {sorted(unknown_plugin)}")
    for field in ("id", "name", "version", "sdk_version", "entrypoint", "type"):
        if field not in plugin:
            raise PluginManifestError(f"missing plugin.{field}")

    plugin_id = _validate_plugin_id(plugin["id"])
    plugin_version = _validate_semver(plugin["version"], "plugin.version")
    sdk_version = _validate_semver(plugin["sdk_version"], "plugin.sdk_version")
    entrypoint = _validate_entrypoint(plugin["entrypoint"])
    plugin_type = plugin["type"]
    if plugin_type not in SUPPORTED_PLUGIN_TYPES:
        raise PluginManifestError(f"unsupported plugin type: {plugin_type!r}")

    compatibility = data["compatibility"]
    if not isinstance(compatibility, dict):
        raise PluginManifestError("compatibility must be an object")
    allowed_compat = {"minimum_hive_version", "required_broker_version", "required_capabilities"}
    unknown_compat = set(compatibility.keys()) - allowed_compat
    if unknown_compat:
        raise PluginManifestError(f"unknown compatibility fields: {sorted(unknown_compat)}")
    if "minimum_hive_version" not in compatibility:
        raise PluginManifestError("missing compatibility.minimum_hive_version")
    _validate_semver(compatibility["minimum_hive_version"], "compatibility.minimum_hive_version")
    required_capabilities = _validate_capabilities(compatibility.get("required_capabilities", []), "compatibility.required_capabilities")

    permissions = data["permissions"]
    if not isinstance(permissions, dict):
        raise PluginManifestError("permissions must be an object")
    allowed_perm = {"requested_capabilities", "filesystem", "network", "secrets"}
    unknown_perm = set(permissions.keys()) - allowed_perm
    if unknown_perm:
        raise PluginManifestError(f"unknown permissions fields: {sorted(unknown_perm)}")
    requested_capabilities = _validate_capabilities(permissions.get("requested_capabilities", []), "permissions.requested_capabilities")
    filesystem = permissions.get("filesystem", [])
    if not isinstance(filesystem, list) or not all(isinstance(x, str) for x in filesystem):
        raise PluginManifestError("permissions.filesystem must be a list of strings")
    for path in filesystem:
        if WILDCARD_PATTERN.search(path):
            raise PluginManifestError(f"permissions.filesystem wildcard rejected: {path}")
        if path.startswith("/") or path.startswith("\\"):
            raise PluginManifestError(f"permissions.filesystem absolute path rejected: {path}")
    network = permissions.get("network", DEFAULT_NETWORK_POLICY)
    if network not in {"deny", "none"}:
        raise PluginManifestError(f"permissions.network must be deny/none, got {network!r}")
    secrets = permissions.get("secrets", [])
    if not isinstance(secrets, list) or secrets:
        raise PluginManifestError("permissions.secrets must be empty in Milestone 16")

    lifecycle = data["lifecycle"]
    if not isinstance(lifecycle, dict):
        raise PluginManifestError("lifecycle must be an object")
    allowed_lifecycle = {"auto_start"}
    unknown_lifecycle = set(lifecycle.keys()) - allowed_lifecycle
    if unknown_lifecycle:
        raise PluginManifestError(f"unknown lifecycle fields: {sorted(unknown_lifecycle)}")
    auto_start = lifecycle.get("auto_start", DEFAULT_AUTO_START)
    if not isinstance(auto_start, bool):
        raise PluginManifestError("lifecycle.auto_start must be boolean")

    dependencies = data.get("dependencies")
    if dependencies is not None:
        if not isinstance(dependencies, dict):
            raise PluginManifestError("dependencies must be an object")
        allowed_dep = {"python_version", "required_capabilities", "plugin_dependencies"}
        unknown_dep = set(dependencies.keys()) - allowed_dep
        if unknown_dep:
            raise PluginManifestError(f"unknown dependencies fields: {sorted(unknown_dep)}")
        if "plugin_dependencies" in dependencies:
            deps = dependencies["plugin_dependencies"]
            if not isinstance(deps, list) or not all(isinstance(x, str) for x in deps):
                raise PluginManifestError("dependencies.plugin_dependencies must be list of plugin IDs")

    signature = data.get("signature")
    if signature is not None:
        if not isinstance(signature, dict):
            raise PluginManifestError("signature must be an object")
        allowed_sig = {"trust_state", "signature_blob", "publisher_id"}
        unknown_sig = set(signature.keys()) - allowed_sig
        if unknown_sig:
            raise PluginManifestError(f"unknown signature fields: {sorted(unknown_sig)}")

    normalized: Dict[str, Any] = {
        "schema_version": schema_version,
        "plugin": {
            "id": plugin_id,
            "name": str(plugin["name"]),
            "version": plugin_version,
            "sdk_version": sdk_version,
            "entrypoint": entrypoint,
            "type": plugin_type,
        },
        "compatibility": {
            "minimum_hive_version": compatibility["minimum_hive_version"],
            "required_broker_version": compatibility.get("required_broker_version"),
            "required_capabilities": required_capabilities,
        },
        "permissions": {
            "requested_capabilities": requested_capabilities,
            "filesystem": filesystem,
            "network": network,
            "secrets": [],
        },
        "lifecycle": {
            "auto_start": auto_start,
        },
    }
    if dependencies is not None:
        normalized["dependencies"] = dependencies
    if signature is not None:
        normalized["signature"] = signature

    return normalized


def manifest_digest(source: str | Path | bytes) -> str:
    """Return SHA-256 digest of canonical manifest bytes."""
    if isinstance(source, Path):
        data = source.read_bytes()
    elif isinstance(source, bytes):
        data = source
    else:
        data = source.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def manifest_to_json(manifest: Dict[str, Any]) -> str:
    """Canonical JSON representation for signing/comparison."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"))
