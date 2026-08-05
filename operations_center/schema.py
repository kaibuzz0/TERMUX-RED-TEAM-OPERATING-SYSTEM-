"""Stable output schemas for Operations Center views."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class SourceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class View(StrEnum):
    OVERVIEW = "overview"
    SERVICES = "services"
    UPDATES = "updates"
    RECOVERY = "recovery"
    VAULT = "vault"
    BROKER = "broker"
    DIAGNOSTICS = "diagnostics"
    EVENTS = "events"
    CONFIG = "config"


def snapshot_envelope(view: View, snapshot_id: str, status: str, data: dict[str, Any], sources: dict[str, Any], diagnostics: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "view": view.value,
        "snapshot_id": snapshot_id,
        "status": status,
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "sources": sources,
        "data": data,
        "diagnostics": diagnostics,
        "errors": errors,
    }
