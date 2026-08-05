"""Manifest validation against capabilities, intents, and policy."""

from __future__ import annotations

from typing import Any

from hive_broker.capabilities import validate_required, is_mutation
from hive_broker.errors import CapabilityError, ManifestError, PolicyError, ApprovalError
from hive_broker.intents import get_intent
from hive_broker.policy import PolicyProfile, validate_actions_for_policy
from hive_broker.schema import validate_manifest


def validate_task_manifest(raw: dict[str, Any], policy: PolicyProfile) -> dict[str, Any]:
    """Run full manifest validation."""
    manifest = validate_manifest(raw)

    # Required capabilities must be advertised
    validate_required(manifest["required_capabilities"])

    # Allowed actions must be subset of required capabilities
    for action in manifest["allowed_actions"]:
        if action not in manifest["required_capabilities"]:
            raise ManifestError(f"Action {action} not declared in required_capabilities")

    # Intent defines permitted actions
    intent = get_intent(manifest["intent"])
    for action in manifest["allowed_actions"]:
        if action not in intent.allowed_actions:
            raise ManifestError(f"Action {action} not permitted for intent {intent.name}")

    # Read-only consistency
    has_mutation = any(is_mutation(action) for action in manifest["allowed_actions"])
    if manifest["read_only"] and has_mutation:
        raise ManifestError("read_only manifest contains mutating action")
    if not manifest["read_only"] and not has_mutation and intent.read_only:
        raise ManifestError("Intent is read-only but manifest declares read_only=false without mutating action")

    # Timeout within intent limit
    if manifest["timeout_seconds"] > intent.max_timeout:
        raise ManifestError(f"timeout_seconds exceeds intent limit {intent.max_timeout}")

    # Policy check
    validate_actions_for_policy(manifest["allowed_actions"], policy)

    # Approval requirement for mutating actions
    if has_mutation and intent.requires_approval:
        raise ApprovalError("Mutating action requires approval (not yet implemented)")

    return manifest
