"""Audit integration for configuration changes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config_engine.errors import ConfigError


class ConfigAuditLog:
    """Bounded configuration audit log."""

    def __init__(self, log_path: Path):
        self.log_path = log_path

    def record(
        self,
        transaction_id: str,
        action: str,
        profile: str,
        author: str,
        details: dict[str, Any],
    ) -> None:
        """Append a single audit entry. Never logs secrets."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.time(),
            "transaction_id": transaction_id,
            "action": action,
            "profile": profile,
            "author": author,
            "details": _redact_details(details),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")


def _redact_details(details: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact secret-like values."""
    redacted: dict[str, Any] = {}
    for key, value in details.items():
        lower = key.lower()
        if any(s in lower for s in ("secret", "password", "key", "token", "credential", "passphrase")):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _redact_details(value)
        elif isinstance(value, list):
            redacted[key] = [_redact_details(v) if isinstance(v, dict) else v for v in value]
        else:
            redacted[key] = value
    return redacted
