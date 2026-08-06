"""Profile inheritance and resolution."""

from __future__ import annotations

from typing import Any

from config_engine.defaults import BUILTIN_PROFILES
from config_engine.errors import ConfigProfileError


class ProfileResolver:
    """Resolve profile inheritance chains and detect cycles."""

    def __init__(self, user_profiles: dict[str, dict[str, Any]] | None = None) -> None:
        self.user_profiles = user_profiles or {}
        self._builtin = BUILTIN_PROFILES

    def resolve(self, name: str, chain: list[str] | None = None, depth: int = 0) -> dict[str, Any]:
        """Resolve a profile, merging its parent chain."""
        MAX_DEPTH = 8
        if depth > MAX_DEPTH:
            raise ConfigProfileError(f"Profile inheritance depth exceeds maximum {MAX_DEPTH}")
        chain = chain or []
        if name in chain:
            raise ConfigProfileError(f"Circular profile inheritance detected: {' -> '.join(chain + [name])}")

        profile = self._load_profile(name)
        parent = self._parent_name(profile)

        if parent:
            parent_data = self.resolve(parent, chain + [name], depth=depth + 1)
            merged = {}
            for subsystem in set(parent_data.keys()) | set(profile.keys()):
                if subsystem == "_parent":
                    continue
                if subsystem in profile and subsystem in parent_data:
                    merged[subsystem] = _merge_subsystem(parent_data[subsystem], profile[subsystem])
                elif subsystem in profile:
                    merged[subsystem] = profile[subsystem]
                else:
                    merged[subsystem] = parent_data[subsystem]
            return merged
        return {k: v for k, v in profile.items() if k != "_parent"}

    def _load_profile(self, name: str) -> dict[str, Any]:
        if name in self.user_profiles:
            return dict(self.user_profiles[name])
        if name in self._builtin:
            return dict(self._builtin[name]())
        raise ConfigProfileError(f"Unknown profile: {name}")

    def _parent_name(self, profile: dict[str, Any]) -> str | None:
        # User profiles may declare inheritance via top-level _parent key.
        parent = profile.get("_parent")
        if parent is None and "runtime" in profile:
            parent = profile["runtime"].get("parent_profile")
        return parent

    def list_profiles(self) -> list[str]:
        return sorted(set(self._builtin.keys()) | set(self.user_profiles.keys()))

    def is_builtin(self, name: str) -> bool:
        return name in self._builtin


def _merge_subsystem(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge subsystem-level dictionaries; override wins."""
    result = dict(base)
    for k, v in override.items():
        result[k] = v
    return result


def validate_profile_name(name: str) -> None:
    """Ensure profile names are safe identifiers."""
    if not isinstance(name, str):
        raise ConfigProfileError("Profile name must be a string")
    if not name:
        raise ConfigProfileError("Profile name must not be empty")
    invalid = set("\\/:*?\"<>|\n\r\t")
    if any(c in name for c in invalid):
        raise ConfigProfileError(f"Invalid profile name characters: {name!r}")
