"""Bounded Hive broker for Hermes integration."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from hive_broker.audit import AuditLog
from hive_broker.capabilities import get_capabilities
from hive_broker.dispatcher import Dispatcher
from hive_broker.errors import BrokerError
from hive_broker.policy import get_policy
from hive_broker.schema import manifest_digest, validate_manifest
from hive_broker.session import BrokerSession
from hive_broker.stop import stop_session
from hive_broker.transaction import generate_transaction
from hive_broker.validator import validate_task_manifest
from hive_broker.version import check_allowed_since_commit, get_runtime_metadata


class Broker:
    """Bounded broker that accepts validated manifests only."""

    def __init__(self, state_root: Path, log_root: Path, policy_name: str | None = None):
        self.state_root = state_root
        self.log_root = log_root
        self.session = BrokerSession(state_root=state_root)
        self.audit = AuditLog(log_root)
        self.policy = get_policy(policy_name)
        self.dispatcher = Dispatcher(self.session)

    def capabilities(self) -> dict[str, Any]:
        return get_capabilities()

    def validate(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            manifest = validate_task_manifest(raw, self.policy)
            return {"valid": True, "manifest": manifest}
        except BrokerError as e:
            return {"valid": False, "error": str(e)}

    def inspect(self, raw: dict[str, Any]) -> dict[str, Any]:
        result = self.validate(raw)
        if not result["valid"]:
            return result
        manifest = result["manifest"]
        return {
            "valid": True,
            "manifest_digest": manifest_digest(manifest),
            "runtime": get_runtime_metadata(),
            "policy": self.policy.name,
        }

    def run(self, raw: dict[str, Any]) -> dict[str, Any]:
        validated = validate_task_manifest(raw, self.policy)
        check_allowed_since_commit(validated)

        audit_id = self.audit.write({
            "schema_version": 1,
            "task_id": validated["task_id"],
            "requestor": validated["requestor"],
            "intent": validated["intent"],
            "manifest_digest": manifest_digest(validated),
            "approved": False,
            "result": "pending",
        })

        txn = generate_transaction(validated["task_id"], self.session.session_id, audit_id)
        self.session.add_transaction(txn.transaction_id)

        try:
            result = self.dispatcher.run(validated, txn)
            self.audit.write({
                "transaction_id": txn.transaction_id,
                "task_id": txn.task_id,
                "session_id": txn.session_id,
                "audit_id": audit_id,
                "requestor": validated["requestor"],
                "intent": validated["intent"],
                "status": result["status"],
                "duration_ms": result["duration_ms"],
            })
            return result
        except BrokerError as e:
            self.session.remove_transaction(txn.transaction_id)
            raise
        finally:
            self.session.remove_transaction(txn.transaction_id)

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session.session_id,
            "stopped": self.session.is_stopped(),
            "active_transactions": sorted(self.session.active_transactions),
            "policy": self.policy.name,
        }

    def stop(self, transaction_id: str | None = None) -> dict[str, Any]:
        return stop_session(self.session, transaction_id)
