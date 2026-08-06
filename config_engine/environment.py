"""Environment override resolution for the Configuration Engine."""

from __future__ import annotations

import os
from typing import Any

from config_engine.errors import ConfigValidationError


ALLOWED_ENV_VARS = {
    "HIVE_REPO_ROOT",
    "HIVE_CONFIG_ROOT",
    "HIVE_STATE_ROOT",
    "HIVE_LOG_ROOT",
    "HIVE_DATA_ROOT",
    "HIVE_CACHE_ROOT",
    "HIVE_TEMP_ROOT",
    "HIVE_LEGACY_ROOT",
    "HIVE_PROFILE",
}


def get_env_overrides(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Return allowed environment overrides as a runtime configuration fragment."""
    env = env or os.environ
    result: dict[str, Any] = {}

    if env.get("HIVE_REPO_ROOT"):
        result["repo_root"] = env["HIVE_REPO_ROOT"]
    if env.get("HIVE_CONFIG_ROOT"):
        result["config_root"] = env["HIVE_CONFIG_ROOT"]
    if env.get("HIVE_STATE_ROOT"):
        result["state_root"] = env["HIVE_STATE_ROOT"]
    if env.get("HIVE_LOG_ROOT"):
        result["log_root"] = env["HIVE_LOG_ROOT"]
    if env.get("HIVE_DATA_ROOT"):
        result["data_root"] = env["HIVE_DATA_ROOT"]
    if env.get("HIVE_CACHE_ROOT"):
        result["cache_root"] = env["HIVE_CACHE_ROOT"]
    if env.get("HIVE_TEMP_ROOT"):
        result["temp_root"] = env["HIVE_TEMP_ROOT"]
    if env.get("HIVE_LEGACY_ROOT"):
        result["legacy_root"] = env["HIVE_LEGACY_ROOT"]
    if env.get("HIVE_PROFILE"):
        result["profile"] = env["HIVE_PROFILE"]

    return result


def validate_env_var(name: str, value: str) -> None:
    """Validate that an environment variable is allowed and the value is safe."""
    if name not in ALLOWED_ENV_VARS:
        raise ConfigValidationError(f"Unknown environment variable: {name}")
    if not value:
        raise ConfigValidationError(f"Environment variable {name} has empty value")
    if "\n" in value or "\r" in value:
        raise ConfigValidationError(f"Environment variable {name} contains line breaks")


def get_allowed_env_names() -> set[str]:
    """Return the set of allowed environment variable names."""
    return set(ALLOWED_ENV_VARS)
