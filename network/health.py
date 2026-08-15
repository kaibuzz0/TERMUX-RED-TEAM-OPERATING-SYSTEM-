"""Layered network health model.

Hive OS 1.1 deliberately separates health levels so that "SOCKS port
responds" does not mean "Tor is healthy".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class HealthLevel(Enum):
    """Distinct health levels for network/Tor diagnostics."""

    OFF = auto()           # Profile does not expect network capability.
    STARTING = auto()      # Expected component is starting.
    UNAVAILABLE = auto()   # Required component absent/unreachable.
    DEGRADED = auto()      # Some checks pass; not fully healthy.
    AVAILABLE = auto()     # Listener/process reachable (not final).
    HEALTHY = auto()       # All relevant checks pass.
    FAILED = auto()        # Definitive failure or crash.

    def __str__(self) -> str:
        return self.name


class HealthCheck(Enum):
    """Named checks that compose network health."""

    SOCKS_LISTENER = "socks_listener"
    TOR_PROCESS = "tor_process"
    CONTROL_PORT = "control_port"
    BOOTSTRAP = "bootstrap"
    PROXY_REQUEST = "proxy_request"
    TOR_CONFIRMATION = "tor_confirmation"


@dataclass
class HealthReport:
    """Structured health report for a network profile."""

    level: HealthLevel
    profile: str
    overall: str = "unknown"
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": str(self.level),
            "profile": self.profile,
            "overall": self.overall,
            "checks": self.checks,
            "last_error": self.last_error,
        }

    @classmethod
    def from_results(
        cls,
        profile: str,
        results: dict[HealthCheck, tuple[bool, str]],
        last_error: str | None = None,
    ) -> "HealthReport":
        checks: dict[str, dict[str, Any]] = {}
        for check, (ok, detail) in results.items():
            checks[check.value] = {"ok": ok, "detail": detail}

        if all(ok for ok, _ in results.values()):
            level = HealthLevel.HEALTHY
            overall = "healthy"
        elif any(ok for ok, _ in results.values()):
            level = HealthLevel.DEGRADED
            overall = "degraded"
        else:
            level = HealthLevel.UNAVAILABLE
            overall = "unavailable"

        return cls(level=level, profile=profile, overall=overall, checks=checks, last_error=last_error)


def summarize_health(report: HealthReport) -> str:
    lines = [
        f"Profile: {report.profile}",
        f"Overall: {report.overall}",
    ]
    for name, data in report.checks.items():
        status = "PASS" if data.get("ok") else "FAIL"
        lines.append(f"  {name}: {status} ({data.get('detail', '')})")
    if report.last_error:
        lines.append(f"Last error: {report.last_error}")
    return "\n".join(lines)
