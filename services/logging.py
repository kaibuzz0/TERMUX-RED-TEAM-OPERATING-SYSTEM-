"""Bounded, contained service logging."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.errors import ServiceConfigError


def resolve_log_targets(manifest: dict[str, Any], log_root: Path) -> tuple[Path | None, Path | None]:
    """Resolve stdout and stderr log paths under log_root."""
    cfg = manifest.get("logging", {})
    stdout_name = cfg.get("stdout")
    stderr_name = cfg.get("stderr")
    stdout = _resolve(log_root, stdout_name) if stdout_name else None
    stderr = _resolve(log_root, stderr_name) if stderr_name else None
    return stdout, stderr


def _resolve(root: Path, name: str) -> Path:
    if ".." in Path(name).parts or name.startswith(("/", "\\")):
        raise ServiceConfigError(f"Log path must be relative: {name!r}")
    return root / name
