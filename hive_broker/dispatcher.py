"""Broker dispatcher."""

from __future__ import annotations

import time
from typing import Any

from hive_broker.adapters import AdapterError, dispatch as dispatch_adapter
from hive_broker.session import BrokerSession
from hive_broker.transaction import Transaction


class Dispatcher:
    """Execute validated broker actions."""

    def __init__(self, session: BrokerSession):
        self.session = session

    def run(self, manifest: dict[str, Any], txn: Transaction) -> dict[str, Any]:
        start = time.time()
        if self.session.is_stopped():
            return self._result(txn, "cancelled", errors=["session stopped"], start=start)

        results = []
        errors = []
        target_services = manifest.get("target_services", [])
        service = target_services[0] if target_services else None
        for action in manifest["allowed_actions"]:
            if self.session.is_stopped() or txn.transaction_id not in self.session.active_transactions:
                errors.append("transaction cancelled")
                break
            try:
                result = dispatch_adapter(action, txn, {"service": service})
                results.append({"action": action, "result": result})
            except AdapterError as e:
                errors.append(str(e))

        status = "success" if not errors else "failure"
        if errors and any(e == "transaction cancelled" for e in errors):
            status = "cancelled"
        return self._result(txn, status, results, errors, start)

    def _result(self, txn: Transaction, status: str, results: list | None = None, errors: list | None = None, start: float = 0.0) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "transaction_id": txn.transaction_id,
            "task_id": txn.task_id,
            "session_id": txn.session_id,
            "audit_id": txn.audit_id,
            "intent": None,
            "status": status,
            "results": results or [],
            "errors": errors or [],
            "duration_ms": int((time.time() - start) * 1000),
        }
