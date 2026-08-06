"""Actor model and registry."""

from __future__ import annotations

from policy_engine.errors import PolicyValidationError


ACTOR_TYPES = {
    "operator",
    "broker",
    "operations_center",
    "installer",
    "service_supervisor",
    "update_engine",
    "recovery_engine",
    "future_plugin",
    "automation",
}

MUTATION_DISABLED_ACTORS = {"future_plugin", "automation"}


def validate_actor(actor_type: str) -> None:
    if actor_type not in ACTOR_TYPES:
        raise PolicyValidationError(f"Unknown actor type: {actor_type!r}")


def actor_may_mutate(actor_type: str) -> bool:
    """Milestone 15: future_plugin and automation mutation rights are not activated."""
    return actor_type not in MUTATION_DISABLED_ACTORS
