"""Stable view models for Operations Center."""

from __future__ import annotations

from typing import Any


def empty_sources() -> dict[str, Any]:
    return {}


def service_view_model(services: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(services)
    running = sum(1 for s in services if s.get("state") == "RUNNING")
    failed = sum(1 for s in services if s.get("state") == "FAILED")
    crash_loop = sum(1 for s in services if s.get("state") == "CRASH_LOOP")
    disabled = sum(1 for s in services if s.get("state") == "DISABLED")
    legacy = sum(1 for s in services if s.get("classification") == "LEGACY_ONLY")
    return {
        "total": total,
        "running": running,
        "failed": failed,
        "crash_loop": crash_loop,
        "disabled": disabled,
        "legacy_only": legacy,
        "services": services[:100],
    }


def overview_view_model(runtime: Any, broker: Any, services: Any, updates: Any, recovery: Any, vault: Any, diagnostics: list[dict[str, Any]], physical_validation: str | None = None) -> dict[str, Any]:
    return {
        "hive_version": runtime.get("version"),
        "runtime_platform": runtime.get("platform"),
        "broker_version": broker.get("broker_version"),
        "broker_available": broker.get("status") == "ok",
        "service_total": services.get("total", 0),
        "services_running": services.get("running", 0),
        "services_failed": services.get("failed", 0),
        "vault_state": vault.get("state", "UNKNOWN"),
        "update_active_release": updates.get("active_release"),
        "recovery_status": recovery.get("status", "UNKNOWN"),
        "warning_count": sum(1 for d in diagnostics if d.get("severity") in ("WARNING", "ERROR", "CRITICAL")),
        "critical_count": sum(1 for d in diagnostics if d.get("severity") == "CRITICAL"),
        "diagnostic_count": len(diagnostics),
        "snapshot": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "physical_validation": physical_validation or "DEFERRED",
    }
