"""Versioned service manifest schema and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from services.errors import ServiceConfigError


SCHEMA_VERSION = 1

ALLOWED_INTERPRETERS = {"python", "bash", "sh", "direct-executable"}
ALLOWED_RESTART_POLICIES = {"never", "on-failure", "always", "unless-stopped"}
ALLOWED_HEALTH_TYPES = {"process", "command", "tcp-local", "file", "none"}
ALLOWED_SHUTDOWN_SIGNALS = {"TERM", "INT", "HUP", "KILL"}
ALLOWED_PATH_BASES = {
    "repository", "canonical-source", "config-root", "state-root",
    "data-root", "cache-root", "log-root", "temp-root", "active-runtime",
}

SERVICE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _reject_shell_metacharacters(value: str, field: str) -> None:
    bad = {";", "&", "|", "$", "`", "\n", ">", "<", "*", "?", "{", "}"}
    if any(ch in value for ch in bad):
        raise ServiceConfigError(f"{field} contains shell metacharacters: {value!r}")


def validate_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized manifest dict."""
    if not isinstance(raw, dict):
        raise ServiceConfigError("Manifest must be a JSON object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ServiceConfigError(f"Unsupported schema version: {raw.get('schema_version')}")

    name = raw.get("name")
    if not isinstance(name, str) or not SERVICE_NAME_RE.match(name):
        raise ServiceConfigError(f"Invalid service name: {name!r}")

    interpreter = raw.get("command", {}).get("interpreter")
    if interpreter not in ALLOWED_INTERPRETERS:
        raise ServiceConfigError(f"Unknown interpreter: {interpreter!r}")

    restart_policy = raw.get("restart", {}).get("policy", "never")
    if restart_policy not in ALLOWED_RESTART_POLICIES:
        raise ServiceConfigError(f"Unknown restart policy: {restart_policy!r}")

    health_type = raw.get("health_check", {}).get("type", "process")
    if health_type not in ALLOWED_HEALTH_TYPES:
        raise ServiceConfigError(f"Unknown health-check type: {health_type!r}")

    _validate_path_base(raw.get("command", {}).get("base"), "command.base")
    _validate_path_base(raw.get("working_directory", {}).get("base"), "working_directory.base")

    for arg in raw.get("command", {}).get("args", []):
        if not isinstance(arg, str):
            raise ServiceConfigError(f"Command args must be strings: {arg!r}")
        _reject_shell_metacharacters(arg, "command.args")
        if ".." in Path(arg).parts:
            raise ServiceConfigError(f"Command arg contains traversal: {arg!r}")

    for dep in raw.get("dependencies", []):
        if not isinstance(dep, str) or not SERVICE_NAME_RE.match(dep):
            raise ServiceConfigError(f"Invalid dependency name: {dep!r}")

    _validate_environment(raw.get("environment", {}))
    _validate_logging(raw.get("logging", {}), name)
    _validate_health(raw.get("health_check", {}), name)

    return raw


def _validate_path_base(base: Any, field: str) -> None:
    if base is None:
        return
    if base not in ALLOWED_PATH_BASES:
        raise ServiceConfigError(f"Unknown path base in {field}: {base!r}")


def _validate_environment(env: Any) -> None:
    if not isinstance(env, dict):
        raise ServiceConfigError("environment must be an object")
    allow = env.get("allow", [])
    if not isinstance(allow, list) or not all(isinstance(x, str) for x in allow):
        raise ServiceConfigError("environment.allow must be a list of strings")
    for name in allow:
        _reject_shell_metacharacters(name, "environment.allow")
    sets = env.get("set", {})
    if not isinstance(sets, dict):
        raise ServiceConfigError("environment.set must be an object")
    for k, v in sets.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ServiceConfigError("environment.set keys and values must be strings")
        _reject_shell_metacharacters(k, "environment.set key")
        _reject_shell_metacharacters(v, "environment.set value")


def _validate_logging(logging: Any, service_name: str) -> None:
    if not isinstance(logging, dict):
        raise ServiceConfigError("logging must be an object")
    for key in ("stdout", "stderr"):
        val = logging.get(key)
        if val is None:
            continue
        if not isinstance(val, str):
            raise ServiceConfigError(f"logging.{key} must be a string")
        _reject_shell_metacharacters(val, f"logging.{key}")
        if ".." in Path(val).parts or val.startswith(("/", "\\")):
            raise ServiceConfigError(f"logging.{key} must be relative: {val!r}")


def _validate_health(health: Any, service_name: str) -> None:
    if not isinstance(health, dict):
        raise ServiceConfigError("health_check must be an object")
    htype = health.get("type", "process")
    if htype == "command":
        args = health.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ServiceConfigError("health_check.args must be a list of strings")
        for a in args:
            _reject_shell_metacharacters(a, "health_check.args")
    elif htype == "tcp-local":
        host = health.get("host", "127.0.0.1")
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise ServiceConfigError(f"health_check.tcp-local host must be loopback: {host!r}")
    elif htype == "file":
        path = health.get("path")
        if not isinstance(path, str):
            raise ServiceConfigError("health_check.file.path must be a string")
        _reject_shell_metacharacters(path, "health_check.file.path")
        if ".." in Path(path).parts or path.startswith(("/", "\\")):
            raise ServiceConfigError(f"health_check.file.path must be relative: {path!r}")


def load_manifest_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ServiceConfigError(f"Invalid JSON in {path}: {e}") from e
    return validate_manifest(data)
