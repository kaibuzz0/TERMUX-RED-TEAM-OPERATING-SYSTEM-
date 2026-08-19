"""Broker policy bridge to the Hive OS Policy Engine.

The broker remains the enforcement point. This module constructs policy
requests and evaluates them through policy_engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config_engine.config import get_config
from hive_broker.errors import PolicyError
from policy_engine.decisions import DecisionState
from policy_engine.engine import PolicyEngine
from policy_engine.requests import PolicyRequest


class PolicyProfile:
    """Compatibility shim mapping broker policy profile to Policy Engine profile."""

    def __init__(self, name: str):
        self.name = name


def get_policy(name: str | None = None) -> PolicyProfile:
    """Return broker policy profile. Defaults to observer."""
    return PolicyProfile(name or "observer")


def validate_actions_for_policy(actions: list[str], profile: PolicyProfile, context: dict[str, Any] | None = None) -> None:
    """Authorize a list of broker actions through the Policy Engine.

    Raises PolicyError if any action is not authorized.
    """
    engine = _engine()
    ctx = _base_context()
    if context:
        ctx.update(context)
    ctx["broker_policy_profile"] = profile.name

    for action in actions:
        request = _make_request("broker", action, ctx)
        decision = engine.evaluate(request, profile_name=profile.name)
        if decision.decision not in (DecisionState.ALLOW,):
            if decision.decision == DecisionState.DENY:
                raise PolicyError(f"Action {action} denied by policy: {decision.reason_code}")
            if decision.decision in (DecisionState.CONFIRM, DecisionState.DEFER):
                raise PolicyError(f"Action {action} requires further authorization: {decision.reason_code}")
            raise PolicyError(f"Action {action} policy evaluation failed: {decision.reason_code}")


def evaluate_action(action: str, profile_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate a single action through the Policy Engine and return a decision dict."""
    engine = _engine()
    ctx = _base_context()
    if context:
        ctx.update(context)
    ctx["broker_policy_profile"] = profile_name
    request = _make_request("broker", action, ctx)
    decision = engine.evaluate(request, profile_name=profile_name)
    return decision.to_dict()


def check_policy(
    *,
    actor_type: str,
    capability: str,
    resource_type: str,
    resource_id: str,
    profile_name: str = "observer",
) -> dict[str, Any]:
    """Evaluate one diagnostic policy request without dispatching any adapter."""
    context = _base_context()
    context["broker_policy_profile"] = profile_name
    request = PolicyRequest.from_dict(
        {
            "schema_version": 1,
            "request_id": "broker-policy-check",
            "actor": {"type": actor_type, "id": "broker-cli"},
            "capability": capability,
            "resource": {"type": resource_type, "id": resource_id},
            "context": context,
        }
    )
    return _engine().evaluate(request, profile_name=profile_name).to_dict()


def _engine() -> PolicyEngine:
    """Lazy singleton Policy Engine."""
    if not hasattr(_engine, "_instance"):
        import os
        repo_root = Path(__file__).resolve().parent.parent
        if not (repo_root / "hive-canonical.json").exists():
            repo_root = Path(os.environ.get("HIVE_REPO_ROOT", Path.cwd()))
        setattr(_engine, "_instance", PolicyEngine.from_repo_root(repo_root))
    return getattr(_engine, "_instance")


def _base_context() -> dict[str, Any]:
    """Base broker policy context, secret-free and deterministic."""
    runtime = get_config("runtime")
    return {
        "configuration_profile": get_config("policy").get("profile_map", {}).get(runtime.get("profile", "default"), "operator"),
        "runtime_mode": "normal",
        "maintenance_mode": False,
        "recovery_mode": False,
        "vault_state": "LOCKED",
        "rollback_available": True,
        "physical_validation_status": "DEFERRED",
    }


def _make_request(actor_type: str, capability: str, context: dict[str, Any]) -> PolicyRequest:
    resource_type = _capability_to_resource_type(capability)
    return PolicyRequest.from_dict({
        "schema_version": 1,
        "request_id": "broker-eval",
        "actor": {"type": actor_type, "id": "broker"},
        "capability": capability,
        "resource": {"type": resource_type, "id": "broker-target"},
        "context": context,
    })


def _capability_to_resource_type(capability: str) -> str:
    if capability.startswith("service."):
        return "service"
    if capability.startswith("vault."):
        return "vault"
    if capability.startswith("update."):
        return "update_bundle"
    if capability.startswith("recovery."):
        return "recovery_bundle"
    if capability.startswith("broker."):
        return "broker_session"
    if capability.startswith("config."):
        return "configuration"
    if capability.startswith("policy."):
        return "runtime"
    return "runtime"
