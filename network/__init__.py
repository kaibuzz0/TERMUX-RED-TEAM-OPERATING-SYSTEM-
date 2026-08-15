"""Hive OS 1.1 modern network foundation.

Provides authoritative network profiles, Tor/Orbot adapters, proxy
execution, and health reporting.
"""

from __future__ import annotations

from network.errors import (
    NetworkError,
    NetworkConfigError,
    NetworkRuntimeError,
    NetworkStateError,
    TorNotAvailableError,
    TorNotHealthyError,
    OrbotNotAvailableError,
    ProxyExecutionError,
    ProfileTransitionError,
)
from network.health import HealthCheck, HealthLevel, HealthReport
from network.manager import NetworkManager
from network.profiles import NetworkProfile, ProfileConfig, default_profile_config
from network.proxy import build_proxy_env, is_proxy_execution_allowed, run_command
from network.state import NetworkState, load_state, save_state, update_profile

__all__ = [
    "NetworkError",
    "NetworkConfigError",
    "NetworkRuntimeError",
    "NetworkStateError",
    "TorNotAvailableError",
    "TorNotHealthyError",
    "OrbotNotAvailableError",
    "ProxyExecutionError",
    "ProfileTransitionError",
    "HealthCheck",
    "HealthLevel",
    "HealthReport",
    "NetworkManager",
    "NetworkProfile",
    "ProfileConfig",
    "default_profile_config",
    "build_proxy_env",
    "is_proxy_execution_allowed",
    "run_command",
    "NetworkState",
    "load_state",
    "save_state",
    "update_profile",
]
