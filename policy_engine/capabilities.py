"""Capability model and registry."""

from __future__ import annotations

from typing import Any

from policy_engine.errors import PolicyValidationError


CAPABILITIES = {
    # Read-only service capabilities
    "service.list",
    "service.status",
    "service.health",
    "service.graph",
    # Mutating service capabilities (high-risk)
    "service.start",
    "service.stop",
    "service.restart",
    "service.reset",
    # Vault capabilities
    "vault.status",
    "vault.unlock",
    "vault.set",
    "vault.get",
    "vault.remove",
    "vault.rotate",
    # Update capabilities
    "update.status",
    "update.inspect",
    "update.plan",
    "update.verify",
    "update.stage",
    "update.apply",
    "update.rollback",
    # Recovery capabilities
    "recovery.status",
    "recovery.diagnose",
    "recovery.verify",
    "recovery.restore",
    "recovery.rollback",
    # Configuration capabilities
    "config.show",
    "config.validate",
    "config.preview",
    "config.commit",
    "config.rollback",
    # Broker capabilities
    "broker.capabilities",
    "broker.status",
    "broker.stop",
    # Policy capabilities (read-only in Milestone 15)
    "policy.status",
    "policy.profiles",
    "policy.explain",
}

READ_ONLY_CAPABILITIES = {
    "service.list",
    "service.status",
    "service.health",
    "service.graph",
    "vault.status",
    "update.status",
    "update.inspect",
    "update.plan",
    "update.verify",
    "recovery.status",
    "recovery.diagnose",
    "recovery.verify",
    "config.show",
    "config.validate",
    "config.preview",
    "broker.capabilities",
    "broker.status",
    "policy.status",
    "policy.profiles",
    "policy.explain",
}

MUTATING_CAPABILITIES = CAPABILITIES - READ_ONLY_CAPABILITIES

SHELL_CAPABILITIES: set[str] = set()  # Shell execution is unsupported


def validate_capability(capability: str) -> None:
    if capability not in CAPABILITIES:
        raise PolicyValidationError(f"Unknown capability: {capability!r}")


def is_read_only(capability: str) -> bool:
    return capability in READ_ONLY_CAPABILITIES


def is_mutating(capability: str) -> bool:
    return capability in MUTATING_CAPABILITIES

def is_mutating_set() -> set[str]:
    """Return the set of all mutating capabilities."""
    return MUTATING_CAPABILITIES


CAPABILITY_METADATA: dict[str, dict[str, Any]] = {
    # Service
    "service.list": {"resource_type": "service", "mutation": False},
    "service.status": {"resource_type": "service", "mutation": False},
    "service.health": {"resource_type": "service", "mutation": False},
    "service.graph": {"resource_type": "service", "mutation": False},
    "service.start": {"resource_type": "service", "mutation": True},
    "service.stop": {"resource_type": "service", "mutation": True},
    "service.restart": {"resource_type": "service", "mutation": True},
    "service.reset": {"resource_type": "service", "mutation": True},
    # Vault
    "vault.status": {"resource_type": "vault", "mutation": False},
    "vault.unlock": {"resource_type": "vault", "mutation": True},
    "vault.set": {"resource_type": "vault", "mutation": True},
    "vault.get": {"resource_type": "vault", "mutation": False},
    "vault.remove": {"resource_type": "vault", "mutation": True},
    "vault.rotate": {"resource_type": "vault", "mutation": True},
    # Update
    "update.status": {"resource_type": "update_bundle", "mutation": False},
    "update.inspect": {"resource_type": "update_bundle", "mutation": False},
    "update.plan": {"resource_type": "update_bundle", "mutation": False},
    "update.verify": {"resource_type": "update_bundle", "mutation": False},
    "update.stage": {"resource_type": "update_bundle", "mutation": True},
    "update.apply": {"resource_type": "update_bundle", "mutation": True},
    "update.rollback": {"resource_type": "update_bundle", "mutation": True},
    # Recovery
    "recovery.status": {"resource_type": "recovery_bundle", "mutation": False},
    "recovery.diagnose": {"resource_type": "recovery_bundle", "mutation": False},
    "recovery.verify": {"resource_type": "recovery_bundle", "mutation": False},
    "recovery.restore": {"resource_type": "recovery_bundle", "mutation": True},
    "recovery.rollback": {"resource_type": "recovery_bundle", "mutation": True},
    # Config
    "config.show": {"resource_type": "configuration", "mutation": False},
    "config.validate": {"resource_type": "configuration", "mutation": False},
    "config.preview": {"resource_type": "configuration", "mutation": False},
    "config.commit": {"resource_type": "configuration", "mutation": True},
    "config.rollback": {"resource_type": "configuration", "mutation": True},
    # Broker
    "broker.capabilities": {"resource_type": "broker_session", "mutation": False},
    "broker.status": {"resource_type": "broker_session", "mutation": False},
    "broker.stop": {"resource_type": "broker_session", "mutation": False},
    # Policy
    "policy.status": {"resource_type": "runtime", "mutation": False},
    "policy.profiles": {"resource_type": "runtime", "mutation": False},
    "policy.explain": {"resource_type": "runtime", "mutation": False},
}


def get_capability_metadata(capability: str) -> dict[str, Any]:
    """Return metadata for a capability."""
    if capability not in CAPABILITIES:
        raise PolicyValidationError(f"Unknown capability: {capability!r}")
    return CAPABILITY_METADATA.get(capability, {"resource_type": "runtime", "mutation": False})
