"""`hive selftest` implementation.

Active diagnostic with mandatory snapshot and restore.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from diagnostics.errors import SelftestError
from diagnostics.finding import Finding
from diagnostics.severity import Severity


@dataclass
class Step:
    name: str
    result: str = "pending"
    duration_ms: float = 0.0
    error: str = ""


def _snapshot_state(network_manager, supervisor) -> dict[str, Any]:
    return {
        "profile": network_manager.current_profile.name,
        "services_running": [
            name for name in supervisor.manifests if supervisor.status(name)["state"] == "RUNNING"
        ],
    }


def _restore_state(network_manager, supervisor, snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    from network.profiles import NetworkProfile
    try:
        target = NetworkProfile.from_name(snapshot["profile"])
        if target == NetworkProfile.DIRECT:
            network_manager.select_direct()
        elif target == NetworkProfile.HOLD:
            network_manager.select_hold()
        elif target == NetworkProfile.ORBOT:
            network_manager.select_orbot()
        elif target == NetworkProfile.TOR:
            # Tor may not be available in test environments; ignore failure.
            try:
                network_manager.select_tor()
            except Exception as exc:
                errors.append(f"Could not restore TOR profile: {exc}")
    except Exception as exc:
        errors.append(f"Profile restore failed: {exc}")

    for name in snapshot.get("services_running", []):
        if name in supervisor.manifests:
            try:
                supervisor.start(name)
            except Exception as exc:
                errors.append(f"Could not restart service {name}: {exc}")
    return errors


def run_selftest(network_manager, supervisor, repo_root: Path, steps: list[Callable] | None = None) -> dict[str, Any]:
    snapshot = _snapshot_state(network_manager, supervisor)
    results: list[Step] = []
    overall = "PASS"

    for fn in (steps or []):
        step = Step(name=getattr(fn, "__name__", str(fn)))
        start = time.monotonic()
        try:
            fn(network_manager, supervisor)
            step.result = "PASS"
        except Exception as exc:
            step.result = "FAIL"
            step.error = str(exc)
            overall = "FAIL"
        step.duration_ms = (time.monotonic() - start) * 1000
        results.append(step)

    restore_errors = _restore_state(network_manager, supervisor, snapshot)
    if restore_errors:
        overall = "FAIL"

    return {
        "overall": overall,
        "snapshot": snapshot,
        "steps": [
            {"name": s.name, "result": s.result, "duration_ms": s.duration_ms, "error": s.error}
            for s in results
        ],
        "restore_errors": restore_errors,
    }
