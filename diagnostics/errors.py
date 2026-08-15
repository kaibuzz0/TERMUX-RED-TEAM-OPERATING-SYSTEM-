"""Diagnostics subsystem errors."""

from __future__ import annotations


class DiagnosticError(Exception):
    """Generic diagnostics failure."""


class AuditMutationError(Exception):
    """Audit attempted to mutate state."""


class SelftestError(Exception):
    """Selftest failed or could not restore state."""
