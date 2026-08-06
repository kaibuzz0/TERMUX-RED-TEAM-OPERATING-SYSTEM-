"""Configuration file loading utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from config_engine.errors import ConfigNotFoundError, ConfigValidationError


def load_json_file(path: Path, max_size_bytes: int = 5 * 1024 * 1024) -> dict[str, Any]:
    """Load and parse a JSON configuration file safely."""
    if not path.exists():
        raise ConfigNotFoundError(f"Configuration file not found: {path}")
    if not path.is_file():
        raise ConfigValidationError(f"Configuration path is not a file: {path}")
    if path.is_symlink():
        raise ConfigValidationError(f"Symlinked configuration file rejected: {path}")

    size = path.stat().st_size
    if size > max_size_bytes:
        raise ConfigValidationError(f"Configuration file too large: {path} ({size} bytes)")

    try:
        raw = path.read_text(encoding="utf-8")
        # Check for invalid UTF-8 surrogate sequences by attempting encode
        raw.encode("utf-8", "surrogatepass")
    except OSError as e:
        raise ConfigNotFoundError(f"Cannot read configuration file {path}: {e}") from e
    except UnicodeError as e:
        raise ConfigValidationError(f"Invalid Unicode in {path}: {e}") from e

    try:
        # object_pairs_hook rejects duplicate keys explicitly.
        data = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigValidationError(f"Configuration root must be an object: {path}")
    return data


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Raise if duplicate JSON keys are present."""
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ConfigValidationError(f"Duplicate JSON key: {key!r}")
        seen.add(key)
    return dict(pairs)


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file with safe loader only."""
    if not path.exists():
        raise ConfigNotFoundError(f"Configuration file not found: {path}")
    if not path.is_file():
        raise ConfigValidationError(f"Configuration path is not a file: {path}")
    if path.is_symlink():
        raise ConfigValidationError(f"Symlinked configuration file rejected: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in {path}: {e}") from e
    except OSError as e:
        raise ConfigNotFoundError(f"Cannot read configuration file {path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigValidationError(f"Configuration root must be an object: {path}")
    return data


def load_config_file(path: Path) -> dict[str, Any]:
    """Load a configuration file by extension."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_json_file(path)
    if suffix in (".yaml", ".yml"):
        return load_yaml_file(path)
    raise ConfigValidationError(f"Unsupported configuration format: {path}")


def discover_user_configs(config_root: Path) -> list[Path]:
    """Return sorted user configuration file paths under config_root."""
    if not config_root.exists():
        return []
    files = []
    for ext in (".json", ".yaml", ".yml"):
        files.extend(config_root.rglob(f"*{ext}"))
    return sorted(files)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON data to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
