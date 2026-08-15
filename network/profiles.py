"""Hive OS network profile definitions and semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class NetworkProfile(Enum):
    """Authoritative Hive network profile states."""

    DIRECT = auto()
    ORBOT = auto()
    TOR = auto()
    HOLD = auto()

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_name(cls, name: str) -> "NetworkProfile":
        name = name.strip().lower()
        # Compatibility aliases from OG Hive
        if name in ("local",):
            return cls.TOR
        if name in ("off",):
            return cls.HOLD
        try:
            return cls[name.upper()]
        except KeyError as exc:
            raise ValueError(f"Unknown network profile: {name!r}") from exc


@dataclass(frozen=True)
class ProfileConfig:
    """Immutable configuration for a profile."""

    name: NetworkProfile
    socks_host: str
    socks_port: int
    control_host: str | None = None
    control_port: int | None = None
    managed_tor: bool = False
    requires_socks: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": str(self.name),
            "socks_host": self.socks_host,
            "socks_port": self.socks_port,
            "control_host": self.control_host,
            "control_port": self.control_port,
            "managed_tor": self.managed_tor,
            "requires_socks": self.requires_socks,
        }


def default_profile_config(profile: NetworkProfile) -> ProfileConfig:
    """Return sensible default configuration for a profile."""
    if profile == NetworkProfile.DIRECT:
        return ProfileConfig(profile, "", 0, managed_tor=False, requires_socks=False)
    if profile == NetworkProfile.HOLD:
        return ProfileConfig(profile, "", 0, managed_tor=False, requires_socks=False)
    if profile == NetworkProfile.ORBOT:
        return ProfileConfig(
            profile,
            socks_host="127.0.0.1",
            socks_port=9050,
            managed_tor=False,
            requires_socks=True,
        )
    if profile == NetworkProfile.TOR:
        return ProfileConfig(
            profile,
            socks_host="127.0.0.1",
            socks_port=9052,
            control_host="127.0.0.1",
            control_port=9051,
            managed_tor=True,
            requires_socks=True,
        )
    raise ValueError(f"Unsupported profile: {profile}")
