"""Requirement model for policy decisions."""

from __future__ import annotations

from typing import Any

from policy_engine.decisions import Requirement
from policy_engine.errors import PolicyValidationError


SUPPORTED_REQUIREMENT_TYPES = {
    "operator_confirmation",
    "vault_unlocked",
    "maintenance_mode",
    "recovery_mode",
    "verified_bundle",
    "rollback_available",
    "physical_validation",
    "specific_profile",
    "specific_capability",
    "fresh_authentication",
    "single_use_approval",
}


def validate_requirement(req: dict[str, Any]) -> None:
    req_type = req.get("type")
    if req_type not in SUPPORTED_REQUIREMENT_TYPES:
        raise PolicyValidationError(f"Unsupported requirement type: {req_type!r}")
    if not isinstance(req_type, str):
        raise PolicyValidationError("Requirement type must be a string")


def requirement_from_dict(req: dict[str, Any]) -> Requirement:
    validate_requirement(req)
    return Requirement(
        type=req["type"],
        status=req.get("status", "pending"),
        scope=req.get("scope"),
        expires_seconds=req.get("expires_seconds"),
        evidence_reference=req.get("evidence_reference"),
        failure_reason=req.get("failure_reason"),
    )


def evaluate_requirement(req: Requirement, context: dict[str, Any]) -> tuple[bool, str | None]:
    """Check whether a requirement is currently satisfied by context.

    Returns (satisfied, failure_reason). The Policy Engine does not satisfy
    requirements; it only evaluates whether the supplied context indicates they
    are met.
    """
    t = req.type
    if t == "operator_confirmation":
        state = context.get("operator_confirmation_state", {})
        if state.get("confirmed") is True:
            return True, None
        return False, "Operator confirmation not provided"
    if t == "vault_unlocked":
        if context.get("vault_state") == "UNLOCKED":
            return True, None
        return False, "Vault is locked"
    if t == "maintenance_mode":
        if context.get("maintenance_mode") is True:
            return True, None
        return False, "Maintenance mode not active"
    if t == "recovery_mode":
        if context.get("recovery_mode") is True:
            return True, None
        return False, "Recovery mode not active"
    if t == "verified_bundle":
        if context.get("update_verification_state") == "VERIFIED":
            return True, None
        return False, "Bundle not verified"
    if t == "rollback_available":
        if context.get("rollback_available") is True:
            return True, None
        return False, "Rollback not available"
    if t == "physical_validation":
        if context.get("physical_validation_status") == "VERIFIED":
            return True, None
        return False, "Physical validation not verified"
    if t == "specific_profile":
        expected = req.scope
        if context.get("configuration_profile") == expected:
            return True, None
        return False, f"Configuration profile is not {expected!r}"
    if t == "specific_capability":
        cap = req.scope
        actor_caps = context.get("actor_capabilities", [])
        if cap in actor_caps:
            return True, None
        return False, f"Actor does not hold capability {cap!r}"
    if t == "fresh_authentication":
        if context.get("actor_authentication_fresh") is True:
            return True, None
        return False, "Authentication not fresh"
    if t == "single_use_approval":
        state = context.get("approval_state", {})
        if state.get("approved") is True and state.get("used") is not True:
            return True, None
        return False, "Single-use approval not available"
    return False, f"Unknown requirement type: {t!r}"
