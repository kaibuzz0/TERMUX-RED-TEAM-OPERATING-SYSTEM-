"""Filesystem permission helpers for Hive logs."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def secure_dir(path: Path) -> None:
    """Best-effort 0700 on a directory."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        try:
            path.chmod(0o700)
        except (OSError, PermissionError):
            pass


def secure_file(path: Path) -> None:
    """Best-effort 0600 on a file."""
    if os.name == "posix" and path.exists():
        try:
            path.chmod(0o600)
        except (OSError, PermissionError):
            pass
