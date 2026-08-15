"""Orbot adapter for Hive OS.

Orbot is optional.  Hive must boot without it.  We only report Orbot as
usable when the configured SOCKS endpoint is actually reachable.
"""

from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from network.errors import OrbotNotAvailableError


@dataclass(frozen=True)
class OrbotEndpoints:
    socks_host: str
    socks_port: int


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        return s.connect_ex((host, port)) == 0


def _can_launch_activity() -> bool:
    """Check whether Android `am` activity launcher is available."""
    am = Path("/system/bin/am")
    if not am.is_file():
        am = Path("/data/data/com.termux/files/usr/bin/am")
    return am.is_file()


class OrbotAdapter:
    """Optional Orbot integration."""

    def __init__(self, endpoints: OrbotEndpoints):
        self.endpoints = endpoints

    def health(self) -> dict[str, Any]:
        reachable = _port_available(self.endpoints.socks_host, self.endpoints.socks_port)
        return {
            "socks_reachable": reachable,
            "socks_host": self.endpoints.socks_host,
            "socks_port": self.endpoints.socks_port,
            "activity_launcher_available": _can_launch_activity(),
            "detail": "SOCKS reachable" if reachable else "SOCKS not reachable (open Orbot?)",
        }

    def usable(self) -> tuple[bool, str]:
        h = self.health()
        if h["socks_reachable"]:
            return True, "Orbot SOCKS reachable"
        return False, h["detail"]

    def launch_ui(self) -> dict[str, Any]:
        if not _can_launch_activity():
            raise OrbotNotAvailableError("Android activity manager not available")
        try:
            result = subprocess.run(
                ["am", "start", "-n", "org.torproject.android/.OrbotMainActivity"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return {"launched": result.returncode == 0, "returncode": result.returncode}
        except FileNotFoundError as exc:
            raise OrbotNotAvailableError("am launcher not found") from exc
        except OSError as exc:
            raise OrbotNotAvailableError(f"Failed to launch Orbot UI: {exc}") from exc
