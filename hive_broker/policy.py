"""Broker policy profiles."""

from __future__ import annotations

from hive_broker.capabilities import BROKER_CAPABILITIES
from hive_broker.errors import PolicyError


class PolicyProfile:
    """Allowlist-based policy."""

    def __init__(self, name: str, allowed_capabilities: frozenset[str]):
        self.name = name
        self.allowed_capabilities = allowed_capabilities


POLICIES: dict[str, PolicyProfile] = {
    "observer": PolicyProfile(
        "observer",
        frozenset(c.name for c in BROKER_CAPABILITIES if not c.mutation),
    ),
    "operator": PolicyProfile(
        "operator",
        frozenset(c.name for c in BROKER_CAPABILITIES if c.mutation),
    ),
    "administrator": PolicyProfile(
        "administrator",
        frozenset(c.name for c in BROKER_CAPABILITIES),
    ),
}


def get_policy(name: str | None = None) -> PolicyProfile:
    """Return the active policy profile. Defaults to observer."""
    name = name or "observer"
    if name not in POLICIES:
        raise PolicyError(f"Unknown policy profile: {name}")
    return POLICIES[name]


def validate_actions_for_policy(actions: list[str], profile: PolicyProfile) -> None:
    for action in actions:
        if action not in profile.allowed_capabilities:
            raise PolicyError(f"Action {action} not permitted by {profile.name} policy")
