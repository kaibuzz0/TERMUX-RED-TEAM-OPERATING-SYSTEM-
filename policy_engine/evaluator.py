"""Pure policy evaluation engine."""

from __future__ import annotations

import time
import uuid
from typing import Any

from policy_engine.actors import actor_may_mutate
from policy_engine.capabilities import is_read_only, validate_capability
from policy_engine.decisions import Decision, DecisionState, Requirement
from policy_engine.errors import PolicyEvaluationError, PolicyRequestError
from policy_engine.rules import PolicySet
from policy_engine.requests import PolicyRequest
from policy_engine.requirements import evaluate_requirement
from policy_engine.rules import Rule, match_rules, sort_rules


MAX_RULES = 1024
MAX_CONDITIONS = 64


class PolicyEvaluator:
    """Evaluate policy requests deterministically with no side effects."""

    def __init__(self, policy_set: PolicySet):
        self.policy_set = policy_set
        self._check_bounds()

    def _check_bounds(self) -> None:
        total = sum(len(p.rules) for p in self.policy_set.profiles.values())
        if total > MAX_RULES:
            raise PolicyEvaluationError(f"Policy rule count {total} exceeds maximum {MAX_RULES}")
        for profile in self.policy_set.profiles.values():
            for rule in profile.rules:
                if len(rule.conditions) > MAX_CONDITIONS:
                    raise PolicyEvaluationError(
                        f"Rule {rule.rule_id} has {len(rule.conditions)} conditions (max {MAX_CONDITIONS})"
                    )

    def evaluate(self, request: PolicyRequest, profile_name: str | None = None) -> Decision:
        """Evaluate a request and return a structured decision."""
        decision_id = f"dec-{uuid.uuid4().hex}"
        start = time.monotonic()

        try:
            self._validate_request(request)
            profile = self._select_profile(request, profile_name)
            matched = match_rules(request, profile.rules)
            ordered = sort_rules(matched)

            decision = self._resolve(ordered, request)
            decision = Decision(
                schema_version=1,
                decision_id=decision_id,
                request_id=request.request_id,
                transaction_id=request.transaction_id,
                decision=decision.decision,
                reason_code=decision.reason_code,
                message=decision.message,
                requirements=list(decision.requirements),
                matched_rules=list(decision.matched_rules),
                audit_required=decision.audit_required,
                cacheable=decision.cacheable,
            )
        except PolicyRequestError as e:
            return Decision(
                schema_version=1,
                decision_id=decision_id,
                request_id=request.request_id,
                transaction_id=request.transaction_id,
                decision=DecisionState.DENY,
                reason_code="UNKNOWN_ACTOR" if "actor" in str(e).lower() else "UNKNOWN_CAPABILITY",
                message=f"Request denied: {e}",
                audit_required=True,
                cacheable=False,
            )
        except Exception as e:
            return Decision(
                schema_version=1,
                decision_id=decision_id,
                request_id=request.request_id,
                transaction_id=request.transaction_id,
                decision=DecisionState.ERROR,
                reason_code="POLICY_CONFIGURATION_INVALID",
                message=f"Evaluation failed: {e}",
                audit_required=True,
                cacheable=False,
            )

        duration = time.monotonic() - start
        # Evaluation has no side effects; duration is not persisted here.
        _ = duration
        return decision

    def _validate_request(self, request: PolicyRequest) -> None:
        if not actor_may_mutate(request.actor["type"]) and is_read_only(request.capability) is False:
            raise PolicyRequestError(f"Actor {request.actor['type']!r} is not authorized to request mutations in Milestone 15")
        validate_capability(request.capability)
        # Validate trusted context values. Unknown or fabricated safety context fails closed.
        from policy_engine.requests import CONTEXT_SCHEMA
        try:
            CONTEXT_SCHEMA.validate(request.context)
        except Exception as exc:
            raise PolicyRequestError(f"Context validation failed: {exc}") from exc

    def _select_profile(self, request: PolicyRequest, override: str | None = None) -> Any:
        name = override or request.context.get("broker_policy_profile") or "observer"
        return self.policy_set.get_profile(name)

    def _resolve(self, rules: list[Rule], request: PolicyRequest) -> Decision:
        """Resolve matched rules using deterministic precedence."""
        if not rules:
            return Decision(
                decision=DecisionState.DENY,
                reason_code="DEFAULT_DENY",
                message="No rule matched the request.",
                matched_rules=[],
            )

        # Separate deny and confirm requirements from allows.
        deny_rules = [r for r in rules if r.effect == DecisionState.DENY]
        confirm_rules = [r for r in rules if r.effect == DecisionState.CONFIRM]
        defer_rules = [r for r in rules if r.effect == DecisionState.DEFER]
        allow_rules = [r for r in rules if r.effect == DecisionState.ALLOW]
        error_rules = [r for r in rules if r.effect == DecisionState.ERROR]

        if error_rules:
            rule = error_rules[0]
            return Decision(
                decision=DecisionState.ERROR,
                reason_code=rule.reason_code,
                message=f"Invalid request or configuration: {rule.rule_id}",
                matched_rules=[rule.rule_id],
            )

        if deny_rules:
            rule = deny_rules[0]
            return Decision(
                decision=DecisionState.DENY,
                reason_code=rule.reason_code,
                message=f"Denied by rule {rule.rule_id}",
                matched_rules=[rule.rule_id],
            )

        if defer_rules:
            rule = defer_rules[0]
            satisfied, reason = self._check_requirements(rule, request.context)
            if not satisfied:
                return Decision(
                    decision=DecisionState.DEFER,
                    reason_code=rule.reason_code,
                    message=f"Deferred: {reason}",
                    requirements=list(rule.requirements),
                    matched_rules=[rule.rule_id],
                )
            return Decision(
                decision=DecisionState.DEFER,
                reason_code=rule.reason_code,
                message=f"Deferred by rule {rule.rule_id}",
                requirements=list(rule.requirements),
                matched_rules=[rule.rule_id],
            )

        if confirm_rules:
            rule = confirm_rules[0]
            return Decision(
                decision=DecisionState.CONFIRM,
                reason_code=rule.reason_code,
                message=f"Requires confirmation per rule {rule.rule_id}",
                requirements=list(rule.requirements),
                matched_rules=[rule.rule_id],
            )

        if allow_rules:
            rule = allow_rules[0]
            return Decision(
                decision=DecisionState.ALLOW,
                reason_code=rule.reason_code,
                message=f"Allowed by rule {rule.rule_id}",
                matched_rules=[rule.rule_id],
                audit_required=True,
                cacheable=True,
            )

        return Decision(
            decision=DecisionState.DENY,
            reason_code="DEFAULT_DENY",
            message="No rule authorized the request.",
            matched_rules=[],
        )

    def _check_requirements(self, rule: Rule, context: dict[str, Any]) -> tuple[bool, str | None]:
        for req in rule.requirements:
            satisfied, reason = evaluate_requirement(req, context)
            if not satisfied:
                return False, reason
        return True, None


def evaluate(request: PolicyRequest, policy_set: PolicySet, profile_name: str | None = None) -> Decision:
    """Convenience function for pure evaluation."""
    return PolicyEvaluator(policy_set).evaluate(request, profile_name)
