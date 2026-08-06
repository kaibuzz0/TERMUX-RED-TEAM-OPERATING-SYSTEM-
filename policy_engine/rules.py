"""Declarative policy rules and rule sets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from policy_engine.actors import actor_may_mutate, validate_actor
from policy_engine.capabilities import is_read_only, is_mutating, validate_capability
from policy_engine.conditions import evaluate_condition, validate_condition
from policy_engine.decisions import DecisionState, Requirement
from policy_engine.errors import PolicyValidationError
from policy_engine.requirements import evaluate_requirement, requirement_from_dict
from policy_engine.resources import validate_resource
from policy_engine.schema import validate_id


@dataclass(frozen=True)
class Rule:
    """A declarative policy rule."""

    rule_id: str
    priority: int
    effect: DecisionState
    actors: set[str] | None = None
    capabilities: set[str] | None = None
    resources: set[str] | None = None
    conditions: list[dict[str, Any]] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    reason_code: str = "CAPABILITY_ALLOWED"

    def matches(self, request: "PolicyRequest") -> bool:
        """Check whether this rule matches a request."""
        if self.actors is not None and request.actor["type"] not in self.actors:
            return False
        if self.capabilities is not None and request.capability not in self.capabilities:
            return False
        if self.resources is not None and request.resource["type"] not in self.resources:
            return False
        if self.effect == DecisionState.NOT_APPLICABLE:
            return False
        for cond in self.conditions:
            if not evaluate_condition(cond, self._build_context(request)):
                return False
        return True

    @staticmethod
    def _build_context(request: "PolicyRequest") -> dict[str, Any]:
        return {
            "actor": request.actor,
            "resource": request.resource,
            "capability": request.capability,
            "context": request.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        validate_rule_dict(data)
        effect = DecisionState(data["effect"])
        return cls(
            rule_id=data["rule_id"],
            priority=int(data["priority"]),
            effect=effect,
            actors=set(data["actors"]) if data.get("actors") else None,
            capabilities=set(data["capabilities"]) if data.get("capabilities") else None,
            resources=set(data["resources"]) if data.get("resources") else None,
            conditions=list(data.get("conditions", [])),
            requirements=[requirement_from_dict(r) for r in data.get("requirements", [])],
            reason_code=data.get("reason_code", "CAPABILITY_ALLOWED"),
        )


def validate_rule_dict(data: dict[str, Any]) -> None:
    """Validate a rule dictionary without constructing it."""
    errors: list[str] = []
    if not isinstance(data.get("rule_id"), str):
        errors.append("rule_id must be a string")
    else:
        try:
            validate_id(data["rule_id"], "rule_id")
        except PolicyValidationError as e:
            errors.append(str(e))
    if not isinstance(data.get("priority"), int):
        errors.append("priority must be an integer")
    if data.get("effect") not in {s.value for s in DecisionState}:
        errors.append(f"effect must be one of {[s.value for s in DecisionState]}")
    for field_name, validator in (
        ("actors", validate_actor),
        ("capabilities", validate_capability),
        ("resources", validate_resource),
    ):
        if data.get(field_name):
            if not isinstance(data[field_name], list):
                errors.append(f"{field_name} must be a list")
                continue
            for item in data[field_name]:
                try:
                    validator(item)
                except PolicyValidationError as e:
                    errors.append(str(e))
    if data.get("conditions"):
        if not isinstance(data["conditions"], list):
            errors.append("conditions must be a list")
        else:
            for cond in data["conditions"]:
                try:
                    validate_condition(cond)
                except PolicyValidationError as e:
                    errors.append(str(e))
    if data.get("requirements"):
        if not isinstance(data["requirements"], list):
            errors.append("requirements must be a list")
        else:
            for req in data["requirements"]:
                try:
                    from policy_engine.requirements import validate_requirement
                    validate_requirement(req)
                except PolicyValidationError as e:
                    errors.append(str(e))
    if errors:
        raise PolicyValidationError(f"Invalid rule {data.get('rule_id', '?')}: {'; '.join(errors)}")


@dataclass
class PolicyProfile:
    """A named policy profile containing a set of rules."""

    name: str
    description: str
    rules: list[Rule]
    default_decision: DecisionState = DecisionState.DENY

    def rule_ids(self) -> set[str]:
        return {r.rule_id for r in self.rules}


class PolicySet:
    """Collection of policy profiles with precedence and validation."""

    def __init__(self, profiles: dict[str, PolicyProfile]):
        self.profiles = profiles
        self._validate()

    def _validate(self) -> None:
        for profile in self.profiles.values():
            seen: set[str] = set()
            dupes: set[str] = set()
            for rule in profile.rules:
                if rule.rule_id in seen:
                    dupes.add(rule.rule_id)
                seen.add(rule.rule_id)
            if dupes:
                raise PolicyValidationError(f"Duplicate rule IDs in profile {profile.name}: {dupes}")

    def get_profile(self, name: str) -> PolicyProfile:
        if name not in self.profiles:
            raise PolicyValidationError(f"Unknown policy profile: {name!r}")
        return self.profiles[name]

    def list_profiles(self) -> list[str]:
        return sorted(self.profiles.keys())


def match_rules(request: "PolicyRequest", rules: list[Rule]) -> list[Rule]:
    """Return all rules matching a request, unsorted."""
    return [r for r in rules if r.matches(request)]


def sort_rules(rules: list[Rule]) -> list[Rule]:
    """Sort rules by priority descending, then specificity, then rule_id."""
    def specificity(rule: Rule) -> int:
        score = 0
        if rule.resources:
            score += 10
        if rule.capabilities:
            score += 5
        if rule.actors:
            score += 3
        if rule.conditions:
            score += len(rule.conditions)
        return score
    return sorted(rules, key=lambda r: (-r.priority, -specificity(r), r.rule_id))
