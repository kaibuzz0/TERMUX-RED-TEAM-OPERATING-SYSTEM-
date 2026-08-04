"""Append-only installation journal."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JournalError(Exception):
    """Journal operation failure."""



class InstallJournal:
    """Append-only structured journal for a single transaction."""

    SECRET_KEYS = {"password", "token", "secret", "key", "api_key", "credential", "auth"}

    def __init__(self, journal_dir: Path, transaction_id: str):
        self.journal_dir = journal_dir
        self.transaction_id = transaction_id
        self.journal_file = journal_dir / f"{transaction_id}.jsonl"
        self._sequence = 0

    def _redact(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove values for known secret-like keys."""
        return {k: "[REDACTED]" if k.lower() in self.SECRET_KEYS else v for k, v in data.items()}

    def start(self) -> dict:
        return self.append("start", {}, {})

    def append(self, operation_id: str, operation_type: str, details: dict[str, Any], result: str = "pending", error_code: str = "", rollback_op: dict[str, Any] | None = None) -> dict:
        self._sequence += 1
        entry = {
            "sequence": self._sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": self.transaction_id,
            "operation_id": operation_id,
            "operation_type": operation_type,
            "details": self._redact(details),
            "result": result,
            "error_code": error_code,
            "rollback_operation": rollback_op or {},
            "verification_state": "pending",
        }
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        return entry

    def close(self, result: str) -> dict:
        return self.append("close", "transaction", {}, result=result)

    def read(self) -> list[dict[str, Any]]:
        if not self.journal_file.exists():
            return []
        records = []
        with open(self.journal_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise JournalError(f"Corrupt journal line: {e}")
        return records

    def is_complete(self) -> bool:
        records = self.read()
        if not records:
            return False
        return records[-1].get("operation_id") == "close"
