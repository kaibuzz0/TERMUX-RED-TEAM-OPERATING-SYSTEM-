"""Read-only Operations Center release view."""

from __future__ import annotations

from typing import Any, Dict

from release_engine.registry import ReleaseRegistry


def release_status_view(registry_path: Any | None = None) -> Dict[str, Any]:
    """Return read-only release status for Operations Center."""
    reg = ReleaseRegistry(registry_path) if registry_path else ReleaseRegistry(_default_registry_path())
    active = reg.get_active()
    previous = reg.rollback_eligible()
    return {
        "view": "releases",
        "current": active.__dict__ if active else None,
        "previous": [r.__dict__ for r in previous],
        "count": len(reg.list_releases()),
    }


def _default_registry_path() -> Any:
    from pathlib import Path
    return Path(".hive") / "releases.json"
