"""Structured JSONL audit log for the broker."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from hive_broker.errors import AuditError


_MAX_RECORD_BYTES = 16 * 1024


class AuditLog:
    """Append-only structured audit log."""

    def __init__(self, log_root: Path):
        self.log_dir = log_root / "broker"
        self._path = self.log_dir / "audit.jsonl"

    def write(self, record: dict[str, Any]) -> str:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        audit_id = f"audit-{uuid.uuid4().hex}"
        record["audit_id"] = audit_id
        record["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        if len(line.encode("utf-8")) > _MAX_RECORD_BYTES:
            line = json.dumps({"audit_id": audit_id, "error": "record oversized"}, sort_keys=True)
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            raise AuditError(f"Failed to write audit: {e}") from e
        return audit_id

    def read_transaction(self, txn_id: str) -> list[dict[str, Any]]:
        results = []
        if not self._path.exists():
            return results
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("transaction_id") == txn_id:
                results.append(record)
        return results
