"""Hive OS diagnostics subsystem."""

from __future__ import annotations

from diagnostics.audit import run_audit
from diagnostics.doctor import diagnose
from diagnostics.errors import AuditMutationError, DiagnosticError, SelftestError
from diagnostics.finding import Finding
from diagnostics.health import HealthReport, evaluate_health
from diagnostics.selftest import run_selftest
from diagnostics.severity import SEVERITY_ORDER, Severity

__all__ = [
    "DiagnosticError",
    "AuditMutationError",
    "SelftestError",
    "Severity",
    "SEVERITY_ORDER",
    "Finding",
    "HealthReport",
    "evaluate_health",
    "diagnose",
    "run_audit",
    "run_selftest",
]
