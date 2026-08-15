"""Deterministic diagnostics derived from broker-returned view data."""

from __future__ import annotations

from operations_center.schema import Severity
from operations_center.view_models import service_view_model
from typing import Any


def evaluate(view: str, data: dict[str, Any], sources: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    # broker unavailable
    if sources.get("broker_status", {}).get("status") != "AVAILABLE":
        findings.append(_diag("OC-BRK-001", Severity.ERROR, "broker", "Broker is not available"))

    # missing capability
    advertised = {c["name"] for c in data.get("broker_capabilities", {}).get("capabilities", [])}
    required = ["service.list", "service.status", "service.health", "vault.status", "update.status", "recovery.status", "broker.capabilities"]
    for cap in required:
        if cap not in advertised:
            findings.append(_diag("OC-CAP-001", Severity.ERROR, "broker", f"Required capability not advertised: {cap}"))

    # service crash loops
    services = data.get("services", {})
    if services.get("crash_loop", 0) > 0:
        findings.append(_diag("OC-SVC-001", Severity.CRITICAL, "services", f"{services['crash_loop']} service(s) in crash loop"))

    if services.get("failed", 0) > 0:
        findings.append(_diag("OC-SVC-002", Severity.ERROR, "services", f"{services['failed']} service(s) failed"))

    # legacy-only services present
    if services.get("legacy_only", 0) > 0:
        findings.append(_diag("OC-SVC-003", Severity.WARNING, "services", f"{services['legacy_only']} legacy-only service(s) present"))

    # vault issues
    vault_state = data.get("vault", {}).get("state")
    if vault_state == "CORRUPT":
        findings.append(_diag("OC-VLT-001", Severity.CRITICAL, "vault", "Vault state is corrupt"))
    elif vault_state == "MIGRATION_REQUIRED":
        findings.append(_diag("OC-VLT-002", Severity.WARNING, "vault", "Vault migration required"))

    # update unverified
    if data.get("updates", {}).get("staged_unverified"):
        findings.append(_diag("OC-UPD-001", Severity.WARNING, "updates", "Staged update bundle is unverified"))

    # recovery journal corrupt
    if data.get("recovery", {}).get("journal_corrupt"):
        findings.append(_diag("OC-RCV-001", Severity.ERROR, "recovery", "Recovery journal is corrupt"))

    # physical validation pending
    findings.append(_diag("OC-VAL-001", Severity.INFO, "validation", "Native Termux validation in progress"))

    return findings


def _diag(code: str, severity: Severity, subsystem: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity.value,
        "subsystem": subsystem,
        "message": message,
        "auto_remediation": False,
        "documentation": None,
    }
