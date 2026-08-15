"""`hive doctor` implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diagnostics.finding import Finding
from diagnostics.severity import Severity
from network.profiles import NetworkProfile


def _make_supervisor(repo_root: Path, state_root: Path, log_root: Path):
    from services.registry import ServiceRegistry
    from services.supervisor import Supervisor
    from config_engine import get_config
    svc_cfg = get_config("services")
    registry = ServiceRegistry(repo_root, state_root)
    registry.load([Path(d) for d in svc_cfg.get("manifest_dirs", [])])
    return Supervisor(registry.native, state_root, log_root, {})


def diagnose(network_manager, supervisor, repo_root: Path, state_root: Path, log_root: Path, vault_state: str = "LOCKED") -> list[Finding]:
    findings: list[Finding] = []

    # Network doctor
    profile = network_manager.current_profile
    if profile == NetworkProfile.TOR:
        try:
            network_manager.health()
        except Exception:
            findings.append(Finding(
                "D-NET-001", Severity.WARNING, "network",
                "Tor profile selected but local Tor appears unhealthy",
                {},
                "Verify tor binary is installed or switch profiles.",
            ))
    elif profile == NetworkProfile.ORBOT:
        from network.orbot import OrbotAdapter, OrbotEndpoints
        from network.profiles import default_profile_config
        cfg = default_profile_config(NetworkProfile.ORBOT)
        adapter = OrbotAdapter(OrbotEndpoints(socks_host=cfg.socks_host, socks_port=cfg.socks_port))
        ok, detail = adapter.usable()
        if not ok:
            findings.append(Finding(
                "D-NET-002", Severity.WARNING, "network",
                f"Orbot profile selected but SOCKS is not reachable: {detail}",
                {},
                "Start Orbot and verify its SOCKS listener.",
            ))

    # Service doctor
    try:
        status = supervisor.status()
        for name, svc in status.get("services", {}).items():
            if svc.get("state") == "BLOCKED_NETWORK":
                findings.append(Finding(
                    "D-SVC-001", Severity.WARNING, "services",
                    f"Service {name} is blocked by network requirement",
                    {"service": name},
                    "Switch to a compatible network profile or adjust the service network requirement.",
                ))
            elif svc.get("state") == "CRASH_LOOP":
                findings.append(Finding(
                    "D-SVC-002", Severity.CRITICAL, "services",
                    f"Service {name} is in a crash loop",
                    {"service": name},
                    "Inspect logs with `hive logs {name}` and reset with `hive services reset {name}`.",
                ))
            elif svc.get("state") == "BLOCKED_DEPENDENCY":
                findings.append(Finding(
                    "D-SVC-003", Severity.WARNING, "services",
                    f"Service {name} is blocked by a missing dependency",
                    {"service": name},
                    "Start the required dependency first.",
                ))
    except Exception as exc:
        findings.append(Finding("D-SVC-004", Severity.ERROR, "services", f"Could not inspect services: {exc}", {}))

    # Vault doctor
    if vault_state == "CORRUPT":
        findings.append(Finding("D-VLT-001", Severity.CRITICAL, "vault", "Vault state is corrupt", {}, "Restore vault from backup or re-initialize after verifying trust material."))
    elif vault_state == "MIGRATION_REQUIRED":
        findings.append(Finding("D-VLT-002", Severity.WARNING, "vault", "Vault migration required", {}, "Run vault migration through the documented path."))

    return findings
