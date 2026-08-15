"""Log rotation and retention.

Single canonical rotation engine.  No shell loops, no competing rotators.
"""

from __future__ import annotations

import gzip
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from runtime_logs.errors import LogRuntimeError
from runtime_logs.permissions import secure_dir, secure_file


@dataclass(frozen=True)
class RotationPolicy:
    max_bytes: int = 10 * 1024 * 1024  # 10 MiB
    retention_count: int = 5
    max_age_days: int | None = None


_ROTATED_RE = re.compile(r"\.log\.(\d+)(\.gz)?$")


def _sorted_rotated_files(base_path: Path) -> list[Path]:
    """Return rotated files for base_path ordered newest to oldest."""
    if not base_path.parent.exists():
        return []
    files: list[tuple[int, Path]] = []
    for p in base_path.parent.iterdir():
        match = _ROTATED_RE.search(p.name)
        if not match:
            continue
        if not p.name.startswith(base_path.name):
            continue
        files.append((int(match.group(1)), p))
    files.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in files]


def _compress(path: Path) -> Path:
    gz = path.with_suffix(path.suffix + ".gz")
    with open(path, "rb") as src, gzip.open(gz, "wb") as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()
    secure_file(gz)
    return gz


def rotate(base_path: Path, policy: RotationPolicy | None = None, compress: bool = True) -> dict:
    """Rotate a log file according to policy.

    Does not write to the current log; only archives/reindexes existing
    rotated files and trims retention.
    """
    policy = policy or RotationPolicy()
    if not base_path.exists():
        return {"rotated": False, "reason": "file does not exist"}

    secure_dir(base_path.parent)

    rotated = _sorted_rotated_files(base_path)
    # Reindex from highest index downward to avoid collisions.
    for old in rotated:
        match = _ROTATED_RE.search(old.name)
        if not match:
            continue
        idx = int(match.group(1))
        suffix = ".gz" if old.suffix == ".gz" else ""
        new_name = f"{base_path.name}.{idx + 1}{suffix}"
        new_path = old.with_name(new_name)
        if new_path.exists():
            new_path.unlink()
        old.rename(new_path)

    # Move current log to .log.1
    current = base_path.with_name(f"{base_path.name}.1")
    shutil.move(str(base_path), str(current))
    if compress:
        current = _compress(current)
    else:
        secure_file(current)

    # Trim retention
    all_rotated = _sorted_rotated_files(base_path)
    removed: list[Path] = []
    for old in all_rotated[policy.retention_count:]:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            pass

    return {
        "rotated": True,
        "current_archived": str(current),
        "removed": [str(p) for p in removed],
        "retained": policy.retention_count,
    }


def rotate_if_needed(base_path: Path, policy: RotationPolicy | None = None, compress: bool = True) -> dict:
    """Rotate only if current log exceeds policy.max_bytes."""
    policy = policy or RotationPolicy()
    if not base_path.exists():
        return {"rotated": False, "reason": "file does not exist"}
    if base_path.stat().st_size < policy.max_bytes:
        return {"rotated": False, "reason": "size below threshold"}
    return rotate(base_path, policy, compress)


def apply_retention(base_dir: Path, pattern: str = "*.log*", max_age_days: int | None = None) -> list[Path]:
    """Delete logs under base_dir older than max_age_days if configured."""
    import time
    removed: list[Path] = []
    if max_age_days is None:
        return removed
    cutoff = time.time() - max_age_days * 86400
    for p in base_dir.rglob(pattern):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                removed.append(p)
        except OSError:
            pass
    return removed
