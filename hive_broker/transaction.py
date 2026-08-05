"""Transaction ID generation and propagation."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from hive_broker.errors import TransactionError


_MAX_ID_LEN = 128
_SAFE_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    task_id: str
    session_id: str
    audit_id: str


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or len(value) > _MAX_ID_LEN or not _SAFE_RE.match(value):
        raise TransactionError(f"Invalid {label}: {value!r}")


def generate_transaction(task_id: str, session_id: str, audit_id: str) -> Transaction:
    _validate_id(task_id, "task_id")
    _validate_id(session_id, "session_id")
    _validate_id(audit_id, "audit_id")
    txn_id = f"txn-{uuid.uuid4().hex}"
    return Transaction(transaction_id=txn_id, task_id=task_id, session_id=session_id, audit_id=audit_id)
