"""Operations Center data sources — broker client only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from hive_broker import Broker


@dataclass(frozen=True)
class SourceRequest:
    capability: str
    manifest: dict[str, Any]


def broker_run(state_root: Any, log_root: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    """Execute a single read-only broker manifest."""
    broker = Broker(state_root, log_root)
    return broker.run(manifest)


def make_manifest(intent: str, capability: str, task_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task_id": task_id,
        "requestor": "operations-center",
        "intent": intent,
        "required_capabilities": [capability],
        "allowed_actions": [capability],
        "target_services": [],
        "target_paths": [],
        "read_only": True,
        "timeout_seconds": 10,
        "audit_level": "normal",
    }


SOURCE_TEMPLATES: dict[str, SourceRequest] = {
    "services": SourceRequest(
        "service.list",
        make_manifest("list-services", "service.list", "oc-services-list"),
    ),
    "service_graph": SourceRequest(
        "service.graph",
        make_manifest("validate-service-definitions", "service.graph", "oc-services-graph"),
    ),
    "service_status": SourceRequest(
        "service.status",
        make_manifest("inspect-service-status", "service.status", "oc-services-status"),
    ),
    "service_health": SourceRequest(
        "service.health",
        make_manifest("inspect-service-status", "service.health", "oc-services-health"),
    ),
    "updates": SourceRequest(
        "update.status",
        make_manifest("inspect-update-status", "update.status", "oc-update-status"),
    ),
    "update_plan": SourceRequest(
        "update.plan",
        make_manifest("plan-update", "update.plan", "oc-update-plan"),
    ),
    "recovery_status": SourceRequest(
        "recovery.status",
        make_manifest("diagnose-recovery-state", "recovery.status", "oc-recovery-status"),
    ),
    "recovery_diagnose": SourceRequest(
        "recovery.diagnose",
        make_manifest("diagnose-recovery-state", "recovery.diagnose", "oc-recovery-diagnose"),
    ),
    "vault_status": SourceRequest(
        "vault.status",
        make_manifest("inspect-vault-status", "vault.status", "oc-vault-status"),
    ),
    "broker_capabilities": SourceRequest(
        "broker.capabilities",
        make_manifest("broker-capabilities", "broker.capabilities", "oc-broker-capabilities"),
    ),
    "broker_status": SourceRequest(
        "broker.status",
        make_manifest("broker-status", "broker.status", "oc-broker-status"),
    ),
    "network_status": SourceRequest(
        "network.status",
        make_manifest("network-status", "network.status", "oc-network-status"),
    ),
    "network_health": SourceRequest(
        "network.health",
        make_manifest("network-health", "network.health", "oc-network-health"),
    ),
    "diagnostics_health": SourceRequest(
        "diagnostics.health",
        make_manifest("diagnostics-health", "diagnostics.health", "oc-diagnostics-health"),
    ),
    "diagnostics_doctor": SourceRequest(
        "diagnostics.doctor",
        make_manifest("diagnostics-doctor", "diagnostics.doctor", "oc-diagnostics-doctor"),
    ),
    "diagnostics_audit": SourceRequest(
        "diagnostics.audit",
        make_manifest("diagnostics-audit", "diagnostics.audit", "oc-diagnostics-audit"),
    ),
    "logs_status": SourceRequest(
        "logs.status",
        make_manifest("logs-status", "logs.status", "oc-logs-status"),
    ),
    "termux_status": SourceRequest(
        "termux.integration.status",
        make_manifest("termux-status", "termux.integration.status", "oc-termux-status"),
    ),
}
