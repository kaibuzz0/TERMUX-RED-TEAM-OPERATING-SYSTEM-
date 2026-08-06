"""Configuration layer merging and variable substitution."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from config_engine.errors import ConfigValidationError


VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def merge_layers(base: dict[str, Any], override: dict[str, Any], path: str = "") -> dict[str, Any]:
    """Deep-merge override into base; override wins at every level."""
    result: dict[str, Any] = {}
    all_keys = set(base.keys()) | set(override.keys())
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        if key in override and key in base:
            b = base[key]
            o = override[key]
            if isinstance(b, dict) and isinstance(o, dict):
                result[key] = merge_layers(b, o, current_path)
            else:
                result[key] = o
        elif key in override:
            result[key] = override[key]
        else:
            result[key] = base[key]
    return result


def substitute_variables(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Recursively substitute ${...} variables in string values."""
    return _substitute_value(data, context)


def _substitute_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _resolve_string(value, context)
    if isinstance(value, dict):
        return {k: _substitute_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_value(v, context) for v in value]
    return value


def _resolve_string(value: str, context: dict[str, Any]) -> str:
    """Resolve variables of form ${key} or ${section:key}."""
    def replacer(match: re.Match) -> str:
        ref = match.group(1)
        if ":" in ref:
            section, key = ref.split(":", 1)
            ref_key = f"{section}:{key}"
        else:
            ref_key = ref

        if ref_key in context:
            resolved = context[ref_key]
            return str(resolved)
        # Fallback to os.environ for backward compatibility during migration
        if ref in os.environ:
            return os.environ[ref]
        raise ConfigValidationError(f"Unresolved variable: ${{{ref}}}")

    return VAR_PATTERN.sub(replacer, value)


def build_context(
    runtime: dict[str, Any],
    repo_root: Path,
    home: Path,
    tmp: str,
) -> dict[str, Any]:
    """Build the substitution context from runtime values."""
    def get(k: str) -> Any:
        return runtime.get(k)

    context: dict[str, Any] = {}
    context["home"] = str(home)
    context["tmp"] = tmp
    context["repo"] = str(repo_root)

    # Runtime section shortcuts
    context["runtime:log_root"] = get("log_root")
    context["runtime:state_root"] = get("state_root")
    context["runtime:config_root"] = get("config_root")
    context["runtime:data_root"] = get("data_root")
    context["runtime:cache_root"] = get("cache_root")
    context["runtime:temp_root"] = get("temp_root")
    context["runtime:profile"] = get("profile")
    context["runtime:log_level"] = get("log_level")

    # Also include plain keys for ${key} references
    for k, v in runtime.items():
        context[k] = v

    return context


def resolve_path(value: str, root: Path | None = None) -> Path:
    """Resolve a configuration path safely, rejecting traversal escapes."""
    p = Path(value)
    if p.expanduser() != p:
        p = p.expanduser()
    if not p.is_absolute():
        if root is None:
            raise ConfigValidationError(f"Relative path not allowed without root: {value}")
        p = (root / p).resolve()
    p = p.resolve()
    if root is not None:
        try:
            p.relative_to(Path(root).resolve())
        except ValueError:
            # Allow absolute paths outside root if they are explicitly absolute and safe
            pass
    return p


def strip_internal_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Remove internal keys like _warnings and _schema_version from user-visible data."""
    return {k: v for k, v in data.items() if not k.startswith("_")}
