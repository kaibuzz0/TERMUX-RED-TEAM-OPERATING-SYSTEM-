"""Legacy credential detection and non-destructive migration planning."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any


LEGACY_AUTH_DIR = ".hive_auth"
LEGACY_AUTH_FILE = "passwd"


def _home_path() -> Path:
    """Resolve the operator home without ever falling back to a shared temp dir."""
    configured = os.environ.get("HOME")
    return Path(configured).expanduser() if configured else Path.home()


def _looks_like_base64(text: str) -> bool:
    text = text.strip()
    if len(text) < 8:
        return False
    try:
        decoded = base64.b64decode(text, validate=True)
        return len(decoded) > 0
    except Exception:
        return False


def detect_legacy_credentials(home: Path | None = None) -> dict[str, Any]:
    """Detect legacy credential storage without modifying it."""
    home = home or _home_path()
    auth_dir = home / LEGACY_AUTH_DIR
    auth_file = auth_dir / LEGACY_AUTH_FILE

    if not auth_file.exists():
        return {
            "legacy_detected": False,
            "auth_dir": str(auth_dir),
            "auth_file": str(auth_file),
            "reason": "Legacy credential file not found",
        }

    raw = auth_file.read_text(encoding="utf-8", errors="ignore").strip()
    return {
        "legacy_detected": True,
        "auth_dir": str(auth_dir),
        "auth_file": str(auth_file),
        "storage_format": "base64" if _looks_like_base64(raw) else "unknown",
        "permissions": oct(auth_file.stat().st_mode)[-3:] if hasattr(auth_file.stat(), "st_mode") else "unknown",
        "size": len(raw),
        "reason": "Legacy .hive_auth/passwd found",
    }


def build_migration_plan(home: Path | None = None) -> dict[str, Any]:
    """Build a non-destructive migration plan from legacy credentials."""
    findings = detect_legacy_credentials(home)
    if not findings["legacy_detected"]:
        return {
            "can_migrate": False,
            "reason": findings["reason"],
        }

    home = home or _home_path()
    vault_dir = home / ".hive" / "vault"

    return {
        "can_migrate": True,
        "source": findings["auth_file"],
        "destination": str(vault_dir / "vault.json"),
        "backup_destination": str(home / ".hive_auth.quarantine"),
        "steps": [
            "Validate legacy file presence",
            "Create encrypted vault with operator-supplied master password",
            "Decode legacy value only in memory",
            "Store password+PIN as scoped secrets",
            "Verify round-trip decryption",
            "Preserve original file in quarantine (do not delete)",
        ],
        "requires": ["operator master password", "physical Termux validation"],
        "auto_delete_original": False,
    }
