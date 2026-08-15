"""`hive audit` implementation.

READ-ONLY by contract.  This module never mutates network, service,
configuration, vault, or autoboot state.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from diagnostics.finding import Finding
from diagnostics.severity import Severity


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"}


def audit_filesystem(state_root: Path, log_root: Path, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    sensitive_dirs = [
        state_root,
        log_root,
        repo_root / "security",
        repo_root / "vault" if (repo_root / "vault").exists() else None,
    ]
    for d in sensitive_dirs:
        if d is None or not d.exists():
            continue
        if os.name == "posix":
            mode = stat.S_IMODE(d.stat().st_mode)
            if mode & 0o077:
                findings.append(Finding(
                    "A-FS-001", Severity.WARNING, "filesystem",
                    f"Directory {d} is group/other accessible (mode {oct(mode)})",
                    {"path": str(d), "mode": oct(mode)},
                    "Restrict to owner-only access where supported.",
                ))
    return findings


def audit_network_config(network_manager) -> list[Finding]:
    from network.profiles import NetworkProfile
    findings: list[Finding] = []
    profile = network_manager.current_profile
    if profile == NetworkProfile.TOR:
        state = network_manager.state
        # Tor config should bind loopback only.
        if state.socks_host and not _is_loopback(state.socks_host):
            findings.append(Finding("A-NET-001", Severity.CRITICAL, "network", f"Tor SOCKS bound to non-loopback {state.socks_host}", {}))
        if state.control_host and not _is_loopback(state.control_host):
            findings.append(Finding("A-NET-002", Severity.CRITICAL, "network", f"Tor ControlPort bound to non-loopback {state.control_host}", {}))
    elif profile == NetworkProfile.ORBOT:
        from network.orbot import OrbotAdapter
        from network.profiles import default_profile_config
        cfg = default_profile_config(NetworkProfile.ORBOT)
        adapter = OrbotAdapter(cfg.socks_host, cfg.socks_port)
        ok, detail = adapter.usable()
        if not ok:
            findings.append(Finding("A-NET-003", Severity.WARNING, "network", f"Orbot selected but not usable: {detail}", {}))
    return findings


def audit_services(supervisor) -> list[Finding]:
    findings: list[Finding] = []
    try:
        status = supervisor.status()
        for name, svc in status.get("services", {}).items():
            manifest = supervisor.manifests.get(name, {})
            if manifest.get("network", {}).get("required") and not manifest.get("network", {}).get("profile"):
                findings.append(Finding(
                    "A-SVC-001", Severity.WARNING, "services",
                    f"Service {name} requires network but does not specify an allowed profile",
                    {"service": name},
                ))
            if svc.get("state") == "CRASH_LOOP":
                findings.append(Finding(
                    "A-SVC-002", Severity.ERROR, "services",
                    f"Service {name} is in a crash loop",
                    {"service": name},
                ))
    except Exception as exc:
        findings.append(Finding("A-SVC-003", Severity.ERROR, "services", f"Could not audit services: {exc}", {}))
    return findings


def run_audit(network_manager, supervisor, repo_root: Path, state_root: Path, log_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(audit_filesystem(state_root, log_root, repo_root))
    findings.extend(audit_network_config(network_manager))
    findings.extend(audit_services(supervisor))
    return findings
