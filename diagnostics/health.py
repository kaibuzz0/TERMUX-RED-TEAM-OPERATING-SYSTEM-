"""`hive health` implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from diagnostics.finding import Finding
from diagnostics.severity import SEVERITY_ORDER, Severity


@dataclass
class HealthReport:
    overall: str  # healthy | degraded | failed
    components: dict[str, str]
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "components": self.components,
            "findings": [f.to_dict() for f in self.findings],
        }


def _worst(components: dict[str, str]) -> str:
    order = {"healthy": 0, "degraded": 1, "failed": 2, "unknown": 3}
    worst = max((order.get(v, 0) for v in components.values()), default=0)
    return {0: "healthy", 1: "degraded", 2: "failed", 3: "failed"}[worst]


def evaluate_health(network_manager, supervisor, broker_available: bool = True, vault_state: str = "LOCKED") -> HealthReport:
    components: dict[str, str] = {"broker": "healthy" if broker_available else "failed"}
    findings: list[Finding] = []

    # Network
    try:
        neth = network_manager.health()
        if neth.level.name == "HEALTHY":
            components["network"] = "healthy"
        elif neth.level.name == "UNAVAILABLE":
            components["network"] = "failed"
            findings.append(Finding("H-NET-001", Severity.ERROR, "network", "Network profile is unavailable", {}))
        else:
            components["network"] = "degraded"
            findings.append(Finding("H-NET-002", Severity.WARNING, "network", "Network is degraded", {"overall": neth.overall}))
    except Exception as exc:
        components["network"] = "failed"
        findings.append(Finding("H-NET-003", Severity.ERROR, "network", f"Network health check failed: {exc}", {}))

    # Supervisor / services
    try:
        status = supervisor.status()
        if status.get("services_failed", 0) > 0:
            components["services"] = "failed"
            findings.append(Finding("H-SVC-001", Severity.ERROR, "services", f"{status['services_failed']} service(s) failed", {}))
        elif status.get("services_blocked", 0) > 0:
            components["services"] = "degraded"
            findings.append(Finding("H-SVC-002", Severity.WARNING, "services", f"{status['services_blocked']} service(s) blocked", {}))
        else:
            components["services"] = "healthy"
    except Exception as exc:
        components["services"] = "failed"
        findings.append(Finding("H-SVC-003", Severity.ERROR, "services", f"Service status check failed: {exc}", {}))

    # Vault
    if vault_state == "CORRUPT":
        components["vault"] = "failed"
        findings.append(Finding("H-VLT-001", Severity.CRITICAL, "vault", "Vault is corrupt", {}))
    elif vault_state in ("MIGRATION_REQUIRED", "LOCKED"):
        components["vault"] = "healthy" if vault_state == "LOCKED" else "degraded"
        if vault_state == "MIGRATION_REQUIRED":
            findings.append(Finding("H-VLT-002", Severity.WARNING, "vault", "Vault migration required", {}))
    else:
        components["vault"] = "unknown"

    return HealthReport(overall=_worst(components), components=components, findings=findings)
