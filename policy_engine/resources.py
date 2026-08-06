"""Resource model and registry."""

from __future__ import annotations

from policy_engine.errors import PolicyValidationError


RESOURCE_TYPES = {
    "service",
    "vault",
    "update_bundle",
    "release",
    "recovery_bundle",
    "configuration",
    "broker_session",
    "transaction",
    "runtime",
    "plugin",
    "workspace",
}


def validate_resource(resource_type: str) -> None:
    if resource_type not in RESOURCE_TYPES:
        raise PolicyValidationError(f"Unknown resource type: {resource_type!r}")
