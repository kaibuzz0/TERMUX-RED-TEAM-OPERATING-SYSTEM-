"""Runtime capability detection for Hive OS.

Detects platform, available tools, and environment variables without mutation,
without requesting permissions, and without installing packages.
"""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class CapabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class PlatformInfo:
    system: str
    release: str
    machine: str
    android: CapabilityState
    termux: CapabilityState
    proot: CapabilityState


@dataclass
class ToolInfo:
    python: CapabilityState
    bash: CapabilityState
    git: CapabilityState
    termux_api: CapabilityState


@dataclass
class EnvironmentInfo:
    prefix: Optional[str]
    home: Optional[str]
    tmpdir: Optional[str]
    termux_version: Optional[str]
    termux_api_version: Optional[str]


@dataclass
class RuntimeReport:
    platform: dict
    tools: dict
    environment: dict
    is_root: CapabilityState


def _has_env(*names: str) -> bool:
    return any(os.environ.get(n) for n in names)


def _safe_which(name: str) -> CapabilityState:
    return CapabilityState.AVAILABLE if shutil.which(name) else CapabilityState.UNAVAILABLE


def _safe_exists(path: Path) -> bool:
    """Return whether *path* exists without leaking host permission errors.

    Runtime detection is informational and must never fail merely because a
    container/CI host exposes a protected procfs or filesystem entry.
    """
    try:
        return path.exists()
    except OSError:
        return False


def _run_version(cmd: list[str]) -> Optional[str]:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe] + cmd[1:],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0].strip()
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        pass
    return None


def detect_android() -> CapabilityState:
    """Detect Android presence without requesting permissions."""
    android_envs = ["ANDROID_ROOT", "ANDROID_DATA", "ANDROID_RUNTIME_ROOT"]
    if any(os.environ.get(e) for e in android_envs):
        return CapabilityState.AVAILABLE
    if _safe_exists(Path("/system/build.prop")):
        return CapabilityState.AVAILABLE
    return CapabilityState.UNVERIFIED


def detect_termux() -> CapabilityState:
    """Detect Termux environment using multiple signals."""
    prefix = os.environ.get("PREFIX")
    if prefix and Path(prefix).name == "usr" and Path(prefix).parent.name.startswith("com.termux"):
        return CapabilityState.AVAILABLE
    if os.environ.get("TERMUX_VERSION"):
        return CapabilityState.AVAILABLE
    if shutil.which("termux-info"):
        return CapabilityState.AVAILABLE
    return CapabilityState.UNAVAILABLE


def detect_proot() -> CapabilityState:
    """Detect PROot/Distro presence without assuming procfs is readable."""
    if os.environ.get("PROOT_DISTRO"):
        return CapabilityState.AVAILABLE
    if os.environ.get("PROOT"):
        return CapabilityState.AVAILABLE
    if _safe_exists(Path("/proc/1/root")) and not os.environ.get("TERMUX_VERSION"):
        # Weak heuristic; do not rely on it for security decisions.
        return CapabilityState.UNVERIFIED
    return CapabilityState.UNAVAILABLE


def detect_root_requested() -> CapabilityState:
    """Report root status without invoking su."""
    try:
        if os.geteuid() == 0:
            return CapabilityState.AVAILABLE
    except AttributeError:
        # Windows does not provide geteuid().
        return CapabilityState.NOT_APPLICABLE
    return CapabilityState.UNAVAILABLE


def detect_termux_api() -> CapabilityState:
    """Detect Termux:API command availability."""
    commands = ["termux-battery-status", "termux-wifi-scaninfo", "termux-toast", "termux-dialog"]
    return CapabilityState.AVAILABLE if any(shutil.which(c) for c in commands) else CapabilityState.UNAVAILABLE


def detect_environment() -> EnvironmentInfo:
    home = os.environ.get("HOME") or str(Path.home())
    return EnvironmentInfo(
        prefix=os.environ.get("PREFIX"),
        home=home,
        tmpdir=os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp",
        termux_version=os.environ.get("TERMUX_VERSION"),
        termux_api_version=_run_version(["termux-api-start", "--version"]) if shutil.which("termux-api-start") else None,
    )


def detect_platform() -> PlatformInfo:
    return PlatformInfo(
        system=platform.system(),
        release=platform.release(),
        machine=platform.machine(),
        android=detect_android(),
        termux=detect_termux(),
        proot=detect_proot(),
    )


def detect_tools() -> ToolInfo:
    return ToolInfo(
        python=_safe_which("python3"),
        bash=_safe_which("bash"),
        git=_safe_which("git"),
        termux_api=detect_termux_api(),
    )


def build_report() -> RuntimeReport:
    return RuntimeReport(
        platform=asdict(detect_platform()),
        tools=asdict(detect_tools()),
        environment=asdict(detect_environment()),
        is_root=detect_root_requested(),
    )
