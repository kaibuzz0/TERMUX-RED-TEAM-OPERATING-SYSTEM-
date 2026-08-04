"""Safe structured service loader for Hive OS.

Reads `etc/services.json` from the canonical source and validates/expandsservice definitions using controlled path bases. Does not start, stop, or mutate services.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from lib.hive_path import (
        PathResolutionError,
        resolve_canonical_source,
        resolve_canonical_launcher,
        resolve_config_root,
        resolve_state_root,
        resolve_data_root,
        resolve_cache_root,
        resolve_log_root,
        resolve_temp_root,
        resolve_repository_root,
    )
except Exception:
    resolve_canonical_source = None
    resolve_canonical_launcher = None


class ServiceLoaderError(Exception):
    """Base exception for service-loader failures."""


class ServiceSchemaError(ServiceLoaderError):
    """Invalid or unsupported service schema."""


class ServicePathError(ServiceLoaderError):
    """Disallowed or unsafe service path."""


class ServiceCommandError(ServiceLoaderError):
    """Unsafe or unsupported command string."""


_ALLOWED_BASES = frozenset({
    "repository",
    "canonical-source",
    "config-root",
    "state-root",
    "data-root",
    "cache-root",
    "log-root",
    "temp-root",
})

_ALLOWED_ENV_VARS = frozenset({
    "HIVE_HOME",
    "HIVE_CONFIG_ROOT",
    "HIVE_STATE_ROOT",
    "HIVE_DATA_ROOT",
    "HIVE_CACHE_ROOT",
    "HIVE_LOG_ROOT",
    "HIVE_TEMP_ROOT",
    "HIVE_OS_ROOT",
    "HIVE_SWARM_ROOT",
    "HIVE_FINAL",
    "HIVE_ETC",
    "HOME",
    "PREFIX",
    "TMPDIR",
})

# Strings that indicate unsafe shell constructs in a command.
_FORBIDDEN_SHELL = re.compile(r"[;&|<>()`$*?[]{}~!]")


def _load_path_resolution(repo_root: Path | None = None) -> dict:
    """Load shared path authority if available."""
    if resolve_canonical_source is None:
        raise ServiceLoaderError("lib/hive_path.py is required for safe service loading")
    if repo_root is None:
        repo_root = resolve_repository_root()
    return {
        "repository": repo_root,
        "canonical-source": resolve_canonical_source(repo_root),
        "config-root": resolve_config_root(home=repo_root.parent),  # tests use repo parent as HOME
        "state-root": resolve_state_root(home=repo_root.parent),
        "data-root": resolve_data_root(home=repo_root.parent),
        "cache-root": resolve_cache_root(home=repo_root.parent),
        "log-root": resolve_log_root(home=repo_root.parent),
        "temp-root": resolve_temp_root(),
    }


def _expand_var_token(token: str) -> str:
    """Expand a single ${VAR} token using allowed variables."""
    if token.startswith("${") and token.endswith("}"):
        var = token[2:-1]
        if var not in _ALLOWED_ENV_VARS:
            raise ServicePathError(f"Disallowed environment variable: {var}")
        val = os.environ.get(var)
        if val is None:
            raise ServicePathError(f"Environment variable unset: {var}")
        return val
    return token


def _resolve_path_object(path_obj: Any, bases: dict, default_base: str = "canonical-source") -> Path:
    """Resolve a structured path object {base, path} or string with ${VAR} to an absolute Path."""
    if isinstance(path_obj, str):
        # Expand any ${VAR} tokens inside the string (e.g., "${HIVE_HOME}/logs/x.log").
        expanded = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
                          lambda m: _expand_var_token("${" + m.group(1) + "}"),
                          path_obj)
        p = Path(expanded)
        if p.is_absolute():
            return p
        if expanded.startswith("/"):
            raise ServicePathError(f"Absolute path not allowed here: {path_obj}")
        base = bases.get(default_base)
        if base is None:
            raise ServicePathError(f"Unknown base: {default_base}")
        return _safe_join(base, expanded)

    if isinstance(path_obj, dict):
        base_name = path_obj.get("base", default_base)
        if base_name not in _ALLOWED_BASES:
            raise ServicePathError(f"Unknown path base: {base_name}")
        rel = path_obj.get("path", "")
        if not isinstance(rel, str):
            raise ServicePathError("Relative path must be a string")
        if rel.startswith("/"):
            raise ServicePathError(f"Relative path must not be absolute: {rel}")
        base = bases[base_name]
        return _safe_join(base, rel)

    raise ServicePathError(f"Invalid path object: {path_obj!r}")


def _safe_join(base: Path, rel: str) -> Path:
    """Join base and relative path, rejecting traversal."""
    if rel == "":
        return base
    joined = (base / rel).resolve()
    base_resolved = base.resolve()
    try:
        joined.relative_to(base_resolved)
    except ValueError:
        raise ServicePathError(f"Path escapes base: {rel}")
    return joined


def _split_command(cmd: str, bases: dict) -> list[str]:
    """Split a safe command string into an argument vector.

    Allowed forms:
      - python3 <script> <args>
      - bash <script> <args>
      - echo <literal>

    Disallowed: shell metacharacters outside of approved ${VAR} tokens.
    """
    if not isinstance(cmd, str):
        raise ServiceCommandError("Command must be a string")

    # Expand allowed ${VAR} tokens first, treating each expansion as a single token.
    def expand_token(m: re.Match) -> str:
        var = m.group(1)
        if var not in _ALLOWED_ENV_VARS:
            raise ServiceCommandError(f"Disallowed variable in command: {var}")
        val = os.environ.get(var)
        if val is None:
            raise ServiceCommandError(f"Unset variable in command: {var}")
        # On Windows, paths may contain backslashes; normalize to forward slashes
        # for tokenization safety. subprocess will handle the OS path on execution.
        return val.replace("\\", "/")

    expanded = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", expand_token, cmd)

    # After token expansion, check for any remaining forbidden shell syntax.
    if _FORBIDDEN_SHELL.search(expanded):
        raise ServiceCommandError(f"Forbidden shell syntax in command: {cmd}")

    # Tokenize respecting single-quoted strings so spaces in expanded paths stay intact.
    tokens = []
    current = ""
    in_quote = False
    for ch in expanded:
        if ch == "'":
            in_quote = not in_quote
            continue
        if ch.isspace() and not in_quote:
            if current:
                tokens.append(current)
                current = ""
            continue
        current += ch
    if current:
        tokens.append(current)
    return tokens


def load_services(path: Path) -> dict:
    """Load and validate service configuration JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ServiceSchemaError("Top-level service config must be an object")

    schema_version = data.get("schema")
    if schema_version not in (1, 2):
        raise ServiceSchemaError(f"Unsupported schema version: {schema_version}")

    if "services" not in data or not isinstance(data["services"], dict):
        raise ServiceSchemaError("Missing 'services' object")

    return data


def _resolve_command_object(cmd_obj: dict, bases: dict, validate_executables: bool, report: dict, field: str):
    """Resolve a structured command object {interpreter, base, path, args}."""
    interpreter = cmd_obj.get("interpreter", "python")
    if interpreter not in ("python", "bash", "sh"):
        raise ServiceCommandError(f"Unsupported interpreter: {interpreter}")

    base_name = cmd_obj.get("base", "canonical-source")
    if base_name not in _ALLOWED_BASES:
        raise ServiceCommandError(f"Unknown path base: {base_name}")

    script_rel = cmd_obj.get("path", "")
    if not isinstance(script_rel, str) or not script_rel:
        raise ServiceCommandError("Command path must be a non-empty string")
    if script_rel.startswith("/"):
        raise ServiceCommandError(f"Command path must be relative: {script_rel}")

    script_path = _safe_join(bases[base_name], script_rel)
    args = cmd_obj.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise ServiceCommandError("args must be a list of strings")

    argv = [interpreter, str(script_path)] + args
    report["resolved"][field] = argv

    if validate_executables:
        exe = shutil.which(interpreter)
        if exe is None:
            report["warnings"].append(f"{field}: interpreter not found in PATH: {interpreter}")
        if not script_path.exists():
            report["warnings"].append(f"{field}: script not found: {script_path}")


def validate_service(name: str, definition: dict, bases: dict, validate_executables: bool = True) -> dict:
    """Validate one service definition and return a resolved, non-mutating report."""
    report = {
        "name": name,
        "enabled": bool(definition.get("auto_start", False)),
        "errors": [],
        "warnings": [],
        "resolved": {},
    }

    # Validate command fields
    for field in ("start", "stop", "status", "restart"):
        if field not in definition:
            continue
        value = definition[field]
        try:
            if isinstance(value, str):
                argv = _split_command(value, bases)
                report["resolved"][field] = argv
                if validate_executables and argv:
                    exe = shutil.which(argv[0])
                    if exe is None:
                        report["warnings"].append(f"{field}: interpreter not found in PATH: {argv[0]}")
            elif isinstance(value, dict):
                _resolve_command_object(value, bases, validate_executables, report, field)
            else:
                raise ServiceCommandError(f"{field} must be a string or structured object")
        except (ServiceCommandError, ServicePathError) as e:
            report["errors"].append(f"{field}: {e}")

    # Validate log path
    log = definition.get("log")
    if log is not None:
        try:
            resolved = _resolve_path_object(log, bases, default_base="log-root")
            log_root = bases.get("log-root")
            if log_root:
                try:
                    resolved.relative_to(log_root.resolve())
                except ValueError:
                    report["warnings"].append(f"log: path outside log-root: {resolved}")
            report["resolved"]["log"] = str(resolved)
        except ServicePathError as e:
            report["errors"].append(f"log: {e}")

    # Validate dependencies
    requires = definition.get("requires", [])
    if not isinstance(requires, list):
        report["errors"].append("requires: must be a list")
    else:
        report["resolved"]["requires"] = requires

    return report


def validate_services_file(path: Path | None = None, validate_executables: bool = False) -> dict:
    """Validate the entire services file. Never starts a service."""
    if path is None:
        if resolve_canonical_source is None:
            raise ServiceLoaderError("Cannot locate services.json without lib/hive_path.py")
        path = resolve_canonical_source() / "etc" / "services.json"

    data = load_services(path)
    bases = _load_path_resolution()

    report = {
        "file": str(path),
        "schema": data.get("schema", data.get("version")),
        "services": {},
        "errors": [],
        "deprecated": [],
    }

    for name, definition in data.get("services", {}).items():
        svc_report = validate_service(name, definition, bases, validate_executables=validate_executables)
        report["services"][name] = svc_report
        if svc_report["errors"]:
            report["errors"].extend([f"{name}: {err}" for err in svc_report["errors"]])

        # Flag legacy command-string entries.
        if isinstance(definition.get("start"), str):
            report["deprecated"].append(f"{name}: start is a legacy command string")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate Hive OS services.json")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--services-file", type=Path, help="Path to services.json")
    args = parser.parse_args()

    report = validate_services_file(args.services_file)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Services file: {report['file']}")
        for name, svc in report["services"].items():
            status = "OK" if not svc["errors"] else "ERR"
            print(f"  [{status}] {name} enabled={svc['enabled']}")
            for err in svc["errors"]:
                print(f"       ERROR: {err}")
            for warn in svc["warnings"]:
                print(f"       WARN:  {warn}")
        if report["deprecated"]:
            print("Deprecated:")
            for dep in report["deprecated"]:
                print(f"  - {dep}")
