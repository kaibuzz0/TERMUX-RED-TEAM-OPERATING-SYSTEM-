"""Proxy environment builder and safe command runner.

Restores the useful OG `hive_proxy_run.sh` behavior without eval or
shell-string reconstruction.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from network.errors import NetworkRuntimeError, ProxyExecutionError
from network.health import HealthCheck, HealthLevel
from network.profiles import NetworkProfile, default_profile_config
from network.state import NetworkState


def build_proxy_env(
    profile: NetworkProfile,
    config: dict[str, Any] | None = None,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return environment for a profile, clearing stale Hive proxy vars.

    DIRECT and HOLD must not leak prior proxy settings.
    """
    env = (base_env or os.environ).copy()
    # Clear stale Hive-managed proxy variables regardless of profile.
    for key in (
        "ALL_PROXY", "all_proxy",
        "HTTP_PROXY", "http_proxy",
        "HTTPS_PROXY", "https_proxy",
        "SOCKS_SERVER", "SOCKS5_SERVER",
    ):
        env.pop(key, None)
    env["NO_PROXY"] = "localhost,127.0.0.1,::1"

    if profile in (NetworkProfile.DIRECT, NetworkProfile.HOLD):
        return env

    cfg = config or default_profile_config(profile).to_dict()
    socks = f"{cfg['socks_host']}:{cfg['socks_port']}"
    proxy_url = f"socks5h://{socks}"
    env["ALL_PROXY"] = proxy_url
    env["all_proxy"] = proxy_url
    # HTTP(S)_PROXY are technically wrong for SOCKS but kept only because
    # some legacy tools consult them.  They point to the same endpoint.
    env["HTTP_PROXY"] = proxy_url
    env["http_proxy"] = proxy_url
    env["HTTPS_PROXY"] = proxy_url
    env["https_proxy"] = proxy_url
    env["SOCKS_SERVER"] = socks
    env["SOCKS5_SERVER"] = socks
    return env


def is_proxy_execution_allowed(state: NetworkState) -> tuple[bool, str]:
    """Determine whether proxy-wrapped execution is currently permitted."""
    profile = state.profile_enum
    if profile == NetworkProfile.HOLD:
        return False, "HOLD profile disables proxy execution"
    if profile == NetworkProfile.DIRECT:
        return True, "DIRECT profile runs without proxy"
    if profile in (NetworkProfile.TOR, NetworkProfile.ORBOT):
        if not state.listener_available:
            return False, f"{state.profile} SOCKS listener is not available"
        return True, f"{state.profile} proxy execution enabled"
    return False, f"Unknown profile: {state.profile}"


def run_command(
    argv: list[str],
    env: dict[str, str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a command vector with the provided environment.

    Returns a CompletedProcess; callers decide exit-code handling.
    """
    if not argv:
        raise ProxyExecutionError("No command provided after `--`")

    # Redact proxies from any captured env representation we might log.
    try:
        result = subprocess.run(
            argv,
            env=env,
            cwd=cwd,
            capture_output=capture_output,
            text=text,
            check=False,
        )
        return result
    except FileNotFoundError as exc:
        raise ProxyExecutionError(f"Command not found: {argv[0]}") from exc
    except OSError as exc:
        raise ProxyExecutionError(f"Failed to execute {argv[0]}: {exc}") from exc
