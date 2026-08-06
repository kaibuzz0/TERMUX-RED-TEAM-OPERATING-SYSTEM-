"""Policy audit record generation.

The Policy Audit component generates structured audit records. It does not
execute policy actions or access secrets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from policy_engine.decisions import Decision
from policy_engine.requests import PolicyRequest


@dataclass
class PolicyAudit:
    """Generate and buffer audit records."""

    records: list[dict[str, Any]] = field(default_factory=list)

    def record(self, request: PolicyRequest, decision: Decision, policy_digest: str) -> None:
        """Generate an audit record. Does not write to disk."""
        entry = {
            "schema_version": 1,
            "timestamp": None,  # filled by writer
            "decision_id": decision.decision_id,
            "request_id": _bounded(request.request_id),
            "transaction_id": _bounded(request.transaction_id),
            "actor_type": request.actor.get("type"),
            "actor_id": _bounded(request.actor.get("id")),
            "capability": request.capability,
            "resource_type": request.resource.get("type"),
            "resource_id": _bounded(request.resource.get("id")),
            "decision": decision.decision.value,
            "reason_code": decision.reason_code,
            "matched_rules": list(decision.matched_rules),
            "requirements": [r.to_dict() for r in decision.requirements],
            "policy_digest": policy_digest,
            "configuration_profile": request.context.get("configuration_profile"),
        }
        self.records.append(entry)

    def clear(self) -> None:
        """Clear buffered records (for testing)."""
        self.records.clear()

    def last_record(self) -> dict[str, Any] | None:
        """Return the most recent buffered record."""
        return self.records[-1] if self.records else None


def _bounded(value: Any, max_len: int = 128) -> Any:
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "[TRUNCATED]"
    return value
