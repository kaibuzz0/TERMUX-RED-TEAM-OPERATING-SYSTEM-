"""Plugin Policy Engine integration.

Plugins use actor type `future_plugin`. Mutating capabilities are denied.
"""

from __future__ import annotations

from typing import Any, Dict

from plugin_sdk.capabilities import MUTATING_CAPABILITIES
from plugin_sdk.errors import PluginPolicyError
from plugin_sdk.identity import PluginIdentity


def _load_policy_engine() -> Any:
    try:
        import policy_engine
        return policy_engine
    except Exception as exc:  # pragma: no cover - optional integration
        raise PluginPolicyError(f"Policy Engine unavailable: {exc}") from exc


def evaluate_plugin_capability(
    identity: PluginIdentity,
    capability: str,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Evaluate a plugin capability request through the Policy Engine.

    This is a broker-mediated stub. In production the Broker constructs the
    PolicyRequest and enforces the decision. The SDK only validates that the
    request is well-formed and non-mutating.
    """
    if capability in MUTATING_CAPABILITIES:
        raise PluginPolicyError(f"mutating capability denied to plugin: {capability}")

    plugin_context = {
        "actor_type": "future_plugin",
        "plugin_id": identity.plugin_id,
        "installation_id": identity.installation_id,
        "capability": capability,
        "runtime_mode": "normal",
    }
    if context:
        plugin_context.update(context)

    return {
        "decision": "ALLOW",
        "policy_decision": "ALLOW",
        "execution_performed": False,
        "actor": identity.actor_id(),
        "capability": capability,
        "context": plugin_context,
    }


def build_plugin_policy_context(
    identity: PluginIdentity,
    granted_capabilities: list[str],
    runtime_mode: str = "normal",
) -> Dict[str, Any]:
    """Build context map for a Policy Request involving a plugin."""
    return {
        "actor_type": "future_plugin",
        "actor_id": identity.actor_id(),
        "plugin_id": identity.plugin_id,
        "installation_id": identity.installation_id,
        "manifest_digest": identity.manifest_digest,
        "granted_capabilities": sorted(granted_capabilities),
        "runtime_mode": runtime_mode,
        "configuration_digest": identity.configuration_digest,
    }
