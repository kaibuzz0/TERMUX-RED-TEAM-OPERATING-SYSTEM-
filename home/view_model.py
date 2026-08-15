"""Hive Home telemetry view model.

Reads authoritative state from existing subsystems and presents it to
Hive Home.  No subsystem logic duplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HiveHomeState:
    runtime: str = "unknown"
    supervisor: str = "unknown"
    network_profile: str = "unknown"
    tor_health: str = "unknown"
    services: str = "unknown"
    policy: str = "unknown"
    broker: str = "unknown"
    vault: str = "unknown"
    trust: str = "unknown"
    termux: str = "unknown"
    notes_preview: str = ""
    errors: list[str] = field(default_factory=list)


def build_home_state(repo_root: Path) -> HiveHomeState:
    state = HiveHomeState(runtime="ONLINE")

    # Network (fast local state)
    try:
        from network import NetworkManager
        from network.health import HealthLevel
        runtime_cfg = _get_runtime_cfg()
        net_mgr = NetworkManager(state_root=Path(runtime_cfg["state_root"]), repo_root=repo_root)
        state.network_profile = net_mgr.current_profile.name
        try:
            report = net_mgr.health()
            if report.level == HealthLevel.HEALTHY:
                state.tor_health = "HEALTHY"
            elif report.level == HealthLevel.UNAVAILABLE:
                state.tor_health = "OFF"
            else:
                state.tor_health = report.level.name
        except Exception:
            state.tor_health = "ERROR"
    except Exception as exc:
        state.network_profile = "ERROR"
        state.tor_health = "ERROR"
        state.errors.append(f"network: {exc}")

    # Supervisor / services
    try:
        from services.registry import ServiceRegistry
        from services.supervisor import Supervisor
        from config_engine import get_config
        svc_cfg = get_config("services")
        runtime_cfg = get_config("runtime")
        registry = ServiceRegistry(repo_root, Path(svc_cfg["state_root"]))
        registry.load([Path(d) for d in svc_cfg.get("manifest_dirs", [])])
        net_mgr2 = NetworkManager(state_root=Path(runtime_cfg["state_root"]), repo_root=repo_root)
        sup = Supervisor(
            registry.native,
            Path(svc_cfg["state_root"]),
            Path(svc_cfg["log_root"]),
            {},
            network_manager=net_mgr2,
        )
        status = sup.status()
        total = status.get("services_configured", 0)
        running = status.get("services_running", 0)
        blocked = status.get("services_blocked", 0)
        failed = status.get("services_failed", 0)
        if failed:
            state.services = f"{running}/{total} RUNNING / {failed} FAILED"
            state.supervisor = "DEGRADED"
        elif blocked:
            state.services = f"{running}/{total} RUNNING / {blocked} BLOCKED"
            state.supervisor = "DEGRADED"
        else:
            state.services = f"{running}/{total} RUNNING"
            state.supervisor = "HEALTHY" if running > 0 or total == 0 else "IDLE"
    except Exception as exc:
        state.services = "ERROR"
        state.supervisor = "ERROR"
        state.errors.append(f"supervisor: {exc}")

    # Policy / broker / vault / trust / termux — best-effort placeholders
    state.policy = "ENFORCED"
    state.broker = "AVAILABLE"
    state.vault = "LOCKED"
    state.trust = "VERIFIED"
    state.termux = "INTEGRATED"

    # Notes preview
    try:
        from operator.notes import read_notes
        from config_engine import get_config
        cfg = get_config("runtime")
        notes, _ = read_notes(Path(cfg.get("config_root", str(Path.home() / ".config" / "hive"))))
        state.notes_preview = notes[:120].replace("\n", " ")
    except Exception:
        state.notes_preview = ""

    return state


def _get_runtime_cfg() -> dict[str, Any]:
    from config_engine import get_config
    return get_config("runtime")
