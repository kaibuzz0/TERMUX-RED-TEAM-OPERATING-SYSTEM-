"""Approval framework. Mutating actions are disabled in Milestone 12."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from hive_broker.errors import ApprovalError


_APPROVAL_TTL_SECONDS = 300


@dataclass(frozen=True)
class ApprovalKey:
    manifest_digest: str
    transaction_id: str
    actions_digest: str


class ApprovalStore:
    """In-memory approval store."""

    def __init__(self) -> None:
        self._approvals: dict[str, float] = {}

    def request_approval(self, manifest: dict[str, Any], txn_id: str) -> ApprovalKey:
        actions = sorted(manifest["allowed_actions"])
        key = ApprovalKey(
            manifest_digest=_digest(manifest),
            transaction_id=txn_id,
            actions_digest=hashlib.sha256(json.dumps(actions).encode()).hexdigest(),
        )
        return key

    def approve(self, key: ApprovalKey) -> None:
        self._approvals[_key_str(key)] = time.time()

    def consume(self, key: ApprovalKey) -> None:
        s = _key_str(key)
        if s not in self._approvals:
            raise ApprovalError("Approval not found")
        issued = self._approvals.pop(s)
        if time.time() - issued > _APPROVAL_TTL_SECONDS:
            raise ApprovalError("Approval expired")


import json


def _digest(manifest: dict[str, Any]) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _key_str(key: ApprovalKey) -> str:
    return f"{key.manifest_digest}:{key.transaction_id}:{key.actions_digest}"
