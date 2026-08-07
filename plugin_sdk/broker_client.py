"""Stable Broker client for plugins.

Plugins interact with Hive through a bounded, manifest-driven API.
No shell. No arbitrary subprocess strings. Identity injected by trusted runtime.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from plugin_sdk.errors import PluginCapabilityError, PluginExecutionError, PluginPolicyError
from plugin_sdk.identity import PluginIdentity
from plugin_sdk.policy import evaluate_plugin_capability
from plugin_sdk.schema import MAX_RESULT_SIZE, PLUGIN_REQUEST_TIMEOUT


@dataclass(frozen=True, slots=True)
class BrokerResult:
    transaction_id: str
    capability: str
    status: str
    data: Any
    error: str | None = None
    policy_decision: str = "ALLOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "capability": self.capability,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "policy_decision": self.policy_decision,
        }


class PluginClient:
    """Bounded client for plugin-to-Broker requests."""

    def __init__(
        self,
        identity: PluginIdentity,
        granted_capabilities: list[str],
        backend: Callable[[str, Dict[str, Any]], Dict[str, Any]] | None = None,
    ):
        self.identity = identity
        self.granted = set(granted_capabilities)
        self.backend = backend

    def capabilities(self) -> list[str]:
        return sorted(self.granted)

    def request(
        self,
        capability: str,
        resource: str | None = None,
        context: Dict[str, Any] | None = None,
    ) -> BrokerResult:
        if capability not in self.granted:
            raise PluginCapabilityError(f"capability not granted: {capability}")

        transaction_id = str(uuid.uuid4())
        plugin_context = {"transaction_id": transaction_id}
        if resource is not None:
            plugin_context["resource"] = resource
        if context:
            plugin_context.update(context)

        policy_result = evaluate_plugin_capability(self.identity, capability, plugin_context)
        if policy_result.get("policy_decision") != "ALLOW":
            decision = policy_result.get("policy_decision", "DENY")
            raise PluginPolicyError(f"policy denied {capability}: {decision}")

        if self.backend is None:
            return BrokerResult(
                transaction_id=transaction_id,
                capability=capability,
                status="success",
                data=policy_result,
                policy_decision="ALLOW",
            )

        try:
            raw = self.backend(capability, plugin_context)
        except Exception as exc:
            raise PluginExecutionError(f"broker backend error: {exc}") from exc

        if not isinstance(raw, dict):
            raise PluginExecutionError("broker backend returned non-dict result")

        raw_str = str(raw)
        if len(raw_str) > MAX_RESULT_SIZE:
            raise PluginExecutionError("broker result exceeded size limit")

        return BrokerResult(
            transaction_id=transaction_id,
            capability=capability,
            status=raw.get("status", "success"),
            data=raw.get("data"),
            error=raw.get("error"),
            policy_decision=raw.get("policy_decision", "ALLOW"),
        )

    def status(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.identity.plugin_id,
            "actor": self.identity.actor_id(),
            "granted_capabilities": sorted(self.granted),
            "transaction_count": 0,
        }


def create_plugin_client(
    identity: PluginIdentity,
    granted_capabilities: list[str],
    backend: Callable[[str, Dict[str, Any]], Dict[str, Any]] | None = None,
) -> PluginClient:
    return PluginClient(identity=identity, granted_capabilities=granted_capabilities, backend=backend)
