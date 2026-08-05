"""Fixed intent registry for the broker."""

from __future__ import annotations

from dataclasses import dataclass, field

from hive_broker.errors import ManifestError


@dataclass(frozen=True)
class Intent:
    name: str
    allowed_actions: frozenset[str]
    read_only: bool
    max_timeout: int = 300
    requires_approval: bool = False


_INTENTS: dict[str, Intent] = {
    "inspect-service-status": Intent(
        name="inspect-service-status",
        allowed_actions=frozenset({"service.status", "service.health"}),
        read_only=True,
        max_timeout=30,
    ),
    "list-services": Intent(
        name="list-services",
        allowed_actions=frozenset({"service.list"}),
        read_only=True,
        max_timeout=30,
    ),
    "validate-service-definitions": Intent(
        name="validate-service-definitions",
        allowed_actions=frozenset({"service.validate", "service.graph"}),
        read_only=True,
        max_timeout=60,
    ),
    "inspect-vault-status": Intent(
        name="inspect-vault-status",
        allowed_actions=frozenset({"vault.status"}),
        read_only=True,
        max_timeout=30,
    ),
    "inspect-update-status": Intent(
        name="inspect-update-status",
        allowed_actions=frozenset({"update.status", "update.inspect"}),
        read_only=True,
        max_timeout=60,
    ),
    "plan-update": Intent(
        name="plan-update",
        allowed_actions=frozenset({"update.plan"}),
        read_only=True,
        max_timeout=120,
    ),
    "verify-update-bundle": Intent(
        name="verify-update-bundle",
        allowed_actions=frozenset({"update.verify"}),
        read_only=True,
        max_timeout=120,
    ),
    "diagnose-recovery-state": Intent(
        name="diagnose-recovery-state",
        allowed_actions=frozenset({"recovery.status", "recovery.diagnose"}),
        read_only=True,
        max_timeout=120,
    ),
    "verify-recovery-bundle": Intent(
        name="verify-recovery-bundle",
        allowed_actions=frozenset({"recovery.verify", "recovery.inspect"}),
        read_only=True,
        max_timeout=120,
    ),
    "stop-broker-task": Intent(
        name="stop-broker-task",
        allowed_actions=frozenset({"broker.stop"}),
        read_only=False,
        max_timeout=10,
    ),
}


def get_intent(name: str) -> Intent:
    if name not in _INTENTS:
        raise ManifestError(f"Unknown intent: {name}")
    return _INTENTS[name]
