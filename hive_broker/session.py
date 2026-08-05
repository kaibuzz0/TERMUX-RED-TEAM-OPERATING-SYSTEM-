"""Broker session state."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from hive_broker.errors import SessionError


class BrokerSession:
    """In-memory session with optional disk persistence."""

    def __init__(self, session_id: str | None = None, state_root: Path | None = None):
        self.session_id = session_id or f"sess-{uuid.uuid4().hex}"
        self.state_root = state_root
        self.created_at = time.time()
        self.active_transactions: set[str] = set()
        self.stopped = False
        self.history: list[dict[str, Any]] = []

    def add_transaction(self, txn_id: str) -> None:
        self.active_transactions.add(txn_id)
        self._persist()

    def remove_transaction(self, txn_id: str) -> None:
        self.active_transactions.discard(txn_id)
        self._persist()

    def stop(self) -> None:
        self.stopped = True
        self._persist()

    def is_stopped(self) -> bool:
        return self.stopped

    def stop_transaction(self, txn_id: str) -> bool:
        if txn_id not in self.active_transactions:
            return False
        self.active_transactions.discard(txn_id)
        self._persist()
        return True

    def _persist(self) -> None:
        if self.state_root is None:
            return
        try:
            self.state_root.mkdir(parents=True, exist_ok=True)
            target = self.state_root / f"{self.session_id}.json"
            data = {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "active_transactions": sorted(self.active_transactions),
                "stopped": self.stopped,
                "history": self.history[-100:],
            }
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(target)
        except OSError as e:
            raise SessionError(f"Failed to persist session: {e}") from e
