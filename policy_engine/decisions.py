"""Structured policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from policy_engine.errors import PolicyValidationError


class DecisionState(str, Enum):
    """Initial decision states."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    CONFIRM = "CONFIRM"
    DEFER = "DEFER"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Requirement:
    """A requirement that must be satisfied for ALLOW after a CONFIRM/DEFER decision."""

    type: str
    status: str = "pending"
    scope: str | None = None
    expires_seconds: int | None = None
    evidence_reference: str | None = None
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "status": self.status,
            "scope": self.scope,
            "expires_seconds": self.expires_seconds,
            "evidence_reference": self.evidence_reference,
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True)
class Decision:
    """A structured policy decision."""

    schema_version: int = 1
    decision_id: str = ""
    request_id: str = ""
    transaction_id: str = ""
    decision: DecisionState = DecisionState.DENY
    reason_code: str = "DEFAULT_DENY"
    message: str = "No rule authorized the request."
    requirements: list[Requirement] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    audit_required: bool = True
    cacheable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "transaction_id": self.transaction_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "message": self.message,
            "requirements": [r.to_dict() for r in self.requirements],
            "matched_rules": list(self.matched_rules),
            "audit_required": self.audit_required,
            "cacheable": self.cacheable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Decision":
        decision_str = data.get("decision", "DENY")
        try:
            decision = DecisionState(decision_str)
        except ValueError as e:
            raise PolicyValidationError(f"Invalid decision state: {decision_str}") from e
        return cls(
            schema_version=data.get("schema_version", 1),
            decision_id=data.get("decision_id", ""),
            request_id=data.get("request_id", ""),
            transaction_id=data.get("transaction_id", ""),
            decision=decision,
            reason_code=data.get("reason_code", "DEFAULT_DENY"),
            message=data.get("message", ""),
            requirements=[Requirement(**r) for r in data.get("requirements", [])],
            matched_rules=list(data.get("matched_rules", [])),
            audit_required=data.get("audit_required", True),
            cacheable=data.get("cacheable", False),
        )
