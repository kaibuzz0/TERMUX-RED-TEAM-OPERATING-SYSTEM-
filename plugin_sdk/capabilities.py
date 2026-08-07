"""Capability contract for plugins.

Plugins declare requested capabilities. The authoritative registry is the
Broker + Policy Engine. The SDK may not invent capabilities.
"""

from __future__ import annotations

from typing import AbstractSet, FrozenSet

from plugin_sdk.errors import PluginCapabilityError
from plugin_sdk.schema import SUPPORTED_PLUGIN_TYPES

TYPE_ALLOWED_CAPABILITIES: dict[str, FrozenSet[str]] = {
    "client": frozenset({
        "service.status",
        "service.list",
        "service.health",
        "service.graph",
        "broker.status",
        "broker.capabilities",
        "policy.status",
        "policy.profiles",
        "policy.explain",
        "vault.status",
        "config.read.plugin",
    }),
    "collector": frozenset({
        "service.status",
        "service.list",
        "service.health",
        "service.graph",
        "broker.status",
        "policy.status",
        "config.read.plugin",
    }),
    "renderer": frozenset({
        "config.read.plugin",
    }),
    "validator": frozenset({
        "config.read.plugin",
        "broker.status",
    }),
}

MUTATING_CAPABILITIES: FrozenSet[str] = frozenset({
    "service.start",
    "service.stop",
    "service.restart",
    "update.apply",
    "recovery.restore",
    "config.commit",
    "vault.secret.get",
})


def validate_capability_set(
    requested: list[str],
    broker_advertised: AbstractSet[str],
    profile_allowed: AbstractSet[str],
    plugin_type: str,
) -> list[str]:
    """Return granted capability subset or raise PluginCapabilityError.

    Granted set must be:
    - requested
    - broker-advertised
    - policy/profile-allowed
    - plugin-type-allowed
    """
    if plugin_type not in SUPPORTED_PLUGIN_TYPES:
        raise PluginCapabilityError(f"unsupported plugin type: {plugin_type}")

    type_allowed = TYPE_ALLOWED_CAPABILITIES[plugin_type]
    requested_set = set(requested)

    if not requested_set.issubset(broker_advertised):
        unknown = requested_set - broker_advertised
        raise PluginCapabilityError(f"requested capabilities not advertised by broker: {sorted(unknown)}")

    if not requested_set.issubset(profile_allowed):
        denied = requested_set - profile_allowed
        raise PluginCapabilityError(f"capabilities denied by profile: {sorted(denied)}")

    if not requested_set.issubset(type_allowed):
        type_denied = requested_set - type_allowed
        raise PluginCapabilityError(f"capabilities not allowed for plugin type {plugin_type}: {sorted(type_denied)}")

    # Additional mutating guard even if not in type_allowed.
    mutating_overlap = requested_set & MUTATING_CAPABILITIES
    if mutating_overlap:
        raise PluginCapabilityError(f"mutating capabilities denied to plugins: {sorted(mutating_overlap)}")

    return sorted(requested_set)


def classify_capability(capability: str) -> str:
    """Classify a capability as read-only or mutating."""
    if capability in MUTATING_CAPABILITIES:
        return "mutating"
    return "read-only"
