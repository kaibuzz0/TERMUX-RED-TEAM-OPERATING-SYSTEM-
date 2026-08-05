"""Capability negotiation for the Hive broker."""

from __future__ import annotations

from dataclasses import dataclass

from hive_broker.errors import CapabilityError


BROKER_VERSION = "1.0"
BROKER_MAJOR_VERSION = 1
BROKER_MINOR_VERSION = 0


@dataclass(frozen=True)
class Capability:
    name: str
    mutation: bool
    approval: str  # "none", "manual", "policy"


# Initial read-only capability set. Mutating capabilities are intentionally absent.
BROKER_CAPABILITIES: tuple[Capability, ...] = (
    Capability("service.list", False, "none"),
    Capability("service.show", False, "none"),
    Capability("service.status", False, "none"),
    Capability("service.health", False, "none"),
    Capability("service.validate", False, "none"),
    Capability("service.graph", False, "none"),
    Capability("vault.status", False, "none"),
    Capability("update.status", False, "none"),
    Capability("update.inspect", False, "none"),
    Capability("update.plan", False, "none"),
    Capability("update.verify", False, "none"),
    Capability("recovery.status", False, "none"),
    Capability("recovery.diagnose", False, "none"),
    Capability("recovery.inspect", False, "none"),
    Capability("recovery.verify", False, "none"),
    Capability("broker.capabilities", False, "none"),
    Capability("broker.status", False, "none"),
    Capability("broker.stop", False, "none"),
)

_CAPABILITY_NAMES = frozenset(c.name for c in BROKER_CAPABILITIES)


def get_capabilities() -> dict:
    """Return advertised capability set."""
    return {
        "schema_version": 1,
        "broker_version": BROKER_VERSION,
        "capabilities": [
            {"name": c.name, "mutation": c.mutation, "approval": c.approval}
            for c in sorted(BROKER_CAPABILITIES, key=lambda x: x.name)
        ],
    }


def validate_required(required: list[str]) -> None:
    """Fail if any required capability is not advertised."""
    if not isinstance(required, list):
        raise CapabilityError("required_capabilities must be a list")
    seen: set[str] = set()
    for name in required:
        if not isinstance(name, str):
            raise CapabilityError(f"Capability name must be a string: {name!r}")
        if name in seen:
            raise CapabilityError(f"Duplicate required capability: {name}")
        seen.add(name)
        if name not in _CAPABILITY_NAMES:
            raise CapabilityError(f"Unsupported required capability: {name}")


def is_mutation(capability_name: str) -> bool:
    for c in BROKER_CAPABILITIES:
        if c.name == capability_name:
            return c.mutation
    raise CapabilityError(f"Unknown capability: {capability_name}")
