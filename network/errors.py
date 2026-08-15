"""Network subsystem errors."""

from __future__ import annotations


class NetworkError(Exception):
    """Base network error."""


class NetworkStateError(NetworkError):
    """Persistent state or I/O failure."""


class NetworkConfigError(NetworkError):
    """Invalid network configuration."""


class NetworkRuntimeError(NetworkError):
    """Runtime failure executing a network operation."""


class TorNotAvailableError(NetworkRuntimeError):
    """Tor binary or adapter unavailable on this platform."""


class TorNotHealthyError(NetworkRuntimeError):
    """Tor is not in a healthy state."""


class OrbotNotAvailableError(NetworkRuntimeError):
    """Orbot SOCKS endpoint is not reachable."""


class ProxyExecutionError(NetworkRuntimeError):
    """Proxy-wrapped command execution failed."""


class ProfileTransitionError(NetworkError):
    """Requested profile transition cannot be satisfied."""
