"""Release channels."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from release_engine.errors import ChannelError


class ReleaseChannel(Enum):
    STABLE = "stable"
    BETA = "beta"
    DEVELOPMENT = "development"


_CHANNEL_ORDER = {
    ReleaseChannel.DEVELOPMENT: 0,
    ReleaseChannel.BETA: 1,
    ReleaseChannel.STABLE: 2,
}


def parse_channel(value: str) -> ReleaseChannel:
    try:
        return ReleaseChannel(value.lower())
    except ValueError as exc:
        raise ChannelError(f"unknown release channel: {value}") from exc


def can_install(channel: ReleaseChannel, target_channel: ReleaseChannel) -> bool:
    """Return True if channel can install target_channel, raise ChannelError otherwise.

    Stable cannot install beta/development. Beta cannot install development.
    """
    if _CHANNEL_ORDER[target_channel] < _CHANNEL_ORDER[channel]:
        raise ChannelError(
            f"channel {channel.value} cannot install {target_channel.value}"
        )
    return True
