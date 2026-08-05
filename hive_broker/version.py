"""Version and source-commit compatibility."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from hive_broker.errors import ManifestError


def get_runtime_metadata() -> dict[str, Any]:
    """Return runtime metadata including broker version and optional commit."""
    from hive_broker.capabilities import BROKER_VERSION
    meta = {"broker_version": BROKER_VERSION}
    commit = _resolve_commit()
    if commit:
        meta["source_commit"] = commit
    return meta


def _resolve_commit() -> str | None:
    env = os.environ.get("HIVE_SOURCE_COMMIT")
    if env:
        return env
    try:
        repo = Path(__file__).resolve().parent.parent
        if (repo / ".git").is_dir():
            out = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,
            )
            if out.returncode == 0:
                return out.stdout.strip()
    except Exception:
        pass
    return None


def check_allowed_since_commit(manifest: dict[str, Any]) -> None:
    """Validate optional commit gating using ancestry when Git is available."""
    allowed = manifest.get("allowed_since_commit")
    if not allowed:
        return
    current = _resolve_commit()
    if not current:
        # Packaged runtime without Git cannot validate; allow if capability negotiation passed.
        return
    if current == allowed:
        return
    try:
        repo = Path(__file__).resolve().parent.parent
        out = subprocess.run(
            ["git", "merge-base", "--is-ancestor", allowed, current],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        if out.returncode == 0:
            return
    except Exception:
        pass
    raise ManifestError(f"allowed_since_commit {allowed} is not an ancestor of current runtime")
