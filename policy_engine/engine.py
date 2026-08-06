"""PolicyEngine facade and broker-facing API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from policy_engine.audit import PolicyAudit
from policy_engine.decisions import Decision
from policy_engine.evaluator import PolicyEvaluator, evaluate
from policy_engine.loader import PolicyLoader, load_from_config_engine
from policy_engine.rules import PolicySet
from policy_engine.requests import PolicyRequest


class PolicyEngine:
    """Single authorization authority for Hive OS.

    The Policy Engine evaluates requests and returns structured decisions.
    It does not execute actions, access secrets, or modify configuration.
    """

    def __init__(self, policy_set: PolicySet, audit: PolicyAudit | None = None):
        self.policy_set = policy_set
        self.evaluator = PolicyEvaluator(policy_set)
        self.audit = audit or PolicyAudit()

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None, audit: PolicyAudit | None = None) -> "PolicyEngine":
        """Create an engine from configuration (typically via config_engine)."""
        loader = PolicyLoader(config)
        policy_set = loader.load(config.get("active_profile") if config else None)
        return cls(policy_set, audit=audit)

    @classmethod
    def from_repo_root(cls, repo_root: Path | str | None = None, profile: str | None = None) -> "PolicyEngine":
        """Create an engine using the Configuration Engine as the policy authority."""
        policy_set = load_from_config_engine(repo_root, profile)
        return cls(policy_set)

    def evaluate(self, request: PolicyRequest | dict[str, Any], profile_name: str | None = None) -> Decision:
        """Evaluate a request and optionally record an audit entry."""
        if isinstance(request, dict):
            request = PolicyRequest.from_dict(request)
        decision = self.evaluator.evaluate(request, profile_name)
        self.audit.record(request, decision, self.policy_digest())
        return decision

    def policy_digest(self) -> str:
        """Return a stable digest of loaded policy for audit correlation."""
        # Deterministic summary: profile names + rule ids + priorities
        parts: list[str] = []
        for name in sorted(self.policy_set.profiles.keys()):
            profile = self.policy_set.profiles[name]
            parts.append(name)
            for rule in sorted(profile.rules, key=lambda r: (r.priority, r.rule_id)):
                parts.append(f"{rule.rule_id}:{rule.priority}:{rule.effect.value}")
        return "sha256:" + _stable_hash(",".join(parts))

    def status(self) -> dict[str, Any]:
        """Return read-only policy engine status."""
        return {
            "schema_version": 1,
            "policy_version": 1,
            "profiles": self.policy_set.list_profiles(),
            "default_profile": "observer",
            "active_profile_count": len(self.policy_set.profiles),
            "total_rules": sum(len(p.rules) for p in self.policy_set.profiles.values()),
            "policy_digest": self.policy_digest(),
            "emergency_restrictions": [],
            "physical_validation_status": "DEFERRED",
        }

    def explain(self, capability: str, actor_type: str = "operator", resource_type: str = "service", profile_name: str | None = None) -> dict[str, Any]:
        """Explain what decision would be returned for a capability without executing."""
        request = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "explain-request",
            "actor": {"type": actor_type, "id": "explain-actor"},
            "capability": capability,
            "resource": {"type": resource_type, "id": "explain-resource"},
            "context": {
                "configuration_profile": "production",
                "broker_policy_profile": profile_name or "operator",
                "runtime_mode": "normal",
                "maintenance_mode": False,
                "recovery_mode": False,
                "vault_state": "LOCKED",
                "rollback_available": True,
                "physical_validation_status": "DEFERRED",
            },
        })
        decision = self.evaluator.evaluate(request, profile_name or "operator")
        return {
            "capability": capability,
            "actor_type": actor_type,
            "resource_type": resource_type,
            "decision": decision.decision.value,
            "reason_code": decision.reason_code,
            "requirements": [r.to_dict() for r in decision.requirements],
        }


def _stable_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
