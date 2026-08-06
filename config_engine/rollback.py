"""Configuration rollback surface."""

from __future__ import annotations

from typing import Any

from config_engine.errors import ConfigRollbackError
from config_engine.persistence import ConfigurationStore


def validate_rollback_target(store: ConfigurationStore, txn_id: str) -> dict[str, Any]:
    """Validate that a rollback target exists and is allowed."""
    try:
        target = store.load_transaction(txn_id)
    except Exception as e:
        raise ConfigRollbackError(f"Invalid rollback target: {e}") from e

    meta = target.get("_meta", {})
    if meta.get("immutable"):
        raise ConfigRollbackError(f"Transaction {txn_id} is marked immutable")
    if not meta.get("rollback_available", True):
        raise ConfigRollbackError(f"Transaction {txn_id} does not allow rollback")
    return target


def perform_rollback(store: ConfigurationStore, txn_id: str, author: str) -> dict[str, Any]:
    """Perform rollback to a target transaction, returning the new transaction record."""
    validate_rollback_target(store, txn_id)
    new_txn_id, _ = store.rollback_to(txn_id, author)
    record = store.load_transaction_record(new_txn_id)
    return {"transaction_id": new_txn_id, "record": record}
