"""Non-mutating preflight environment detection."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from installer.schema import CapabilityState, InstallStatus

try:
    from lib.hive_path import resolve_repository_root, resolve_canonical_source, resolve_config_root, resolve_state_root, resolve_data_root, resolve_cache_root, resolve_log_root
    from lib.hive_runtime import detect_platform, detect_tools, build_report
except Exception:
    resolve_repository_root = None
    resolve_canonical_source = None


class PreflightError(Exception):
    """Preflight detection failure."""



class PreflightResult:
    """Container for preflight findings."""

    def __init__(self, env: dict[str, Any], classification: dict[str, CapabilityState], existing: InstallStatus, warnings: list[str], errors: list[str]):
        self.environment = env
        self.classification = classification
        self.existing_installation = existing
        self.warnings = warnings
        self.errors = errors

    def to_dict(self) -> dict:
        return {
            "environment": self.environment,
            "classification": {k: v.value for k, v in self.classification.items()},
            "existing_installation": self.existing_installation.value,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _command_exists(cmd: str) -> CapabilityState:
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=5)
        return CapabilityState.AVAILABLE
    except Exception:
        try:
            subprocess.run([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=5)
            return CapabilityState.AVAILABLE
        except Exception:
            return CapabilityState.UNAVAILABLE


def _detect_architecture() -> str:
    return platform.machine().lower()


def _detect_termux(env: dict[str, str]) -> CapabilityState:
    if env.get("TERMUX_VERSION"):
        return CapabilityState.AVAILABLE
    if Path("/data/data/com.termux").exists():
        return CapabilityState.AVAILABLE
    # Without explicit evidence, on Windows the host cannot be Termux.
    if os.name == "nt" or sys.platform.startswith("win"):
        return CapabilityState.NOT_APPLICABLE
    return CapabilityState.UNKNOWN


def _probe_exists(path: Path) -> tuple[bool, OSError | None]:
    """Probe a path without allowing host permission quirks to abort preflight."""
    try:
        return path.exists(), None
    except OSError as exc:
        return False, exc


def _detect_existing_installation(target_root: Path, env: dict[str, str]) -> tuple[InstallStatus, list[str]]:
    warnings = []
    target_exists, target_error = _probe_exists(target_root)
    if target_error is not None:
        warnings.append(f"Cannot inspect target {target_root}: {target_error}")
        return InstallStatus.CONFLICT, warnings

    root = target_root.resolve() if target_exists else None
    legacy_root = Path("/root/hive")

    if root:
        # Determine if it looks managed or modified.
        manifest = root / ".hive" / "manifest.json"
        manifest_exists, manifest_error = _probe_exists(manifest)
        if manifest_error is not None:
            warnings.append(f"Cannot inspect managed manifest {manifest}: {manifest_error}")
            return InstallStatus.CONFLICT, warnings
        if manifest_exists:
            return InstallStatus.MANAGED_UPGRADE_REQUIRED, warnings
        warnings.append(f"Target {root} exists but has no managed manifest")
        return InstallStatus.CONFLICT, warnings

    legacy_exists, legacy_error = _probe_exists(legacy_root)
    if legacy_error is not None:
        # /root is intentionally inaccessible on many non-root Linux hosts and
        # CI runners. Legacy discovery is advisory, so inability to inspect this
        # unrelated root-owned path must not make clean installs impossible.
        warnings.append(f"Legacy installation path {legacy_root} is not inspectable: {legacy_error}")
    elif legacy_exists:
        warnings.append(f"Legacy installation path {legacy_root} exists")
        return InstallStatus.LEGACY_MIGRATION_REQUIRED, warnings

    hive_home = env.get("HIVE_HOME")
    if hive_home:
        hive_home_path = Path(hive_home)
        hive_home_exists, hive_home_error = _probe_exists(hive_home_path)
        if hive_home_error is not None:
            warnings.append(f"HIVE_HOME {hive_home} is not inspectable: {hive_home_error}")
            return InstallStatus.CONFLICT, warnings
        if hive_home_exists:
            warnings.append(f"HIVE_HOME {hive_home} exists")
            return InstallStatus.CONFLICT, warnings

    return InstallStatus.CLEAN_INSTALL, warnings


def _detect_incomplete_transaction(state_root: Path) -> bool:
    journal = state_root / "install-journal"
    if not journal.exists():
        return False
    # A journal with an open entry means an incomplete transaction.
    for entry in sorted(journal.glob("*.jsonl")):
        last_line = ""
        with open(entry, "r", encoding="utf-8") as f:
            for line in f:
                last_line = line
        if last_line:
            try:
                import json
                record = json.loads(last_line)
                if record.get("result") not in ("completed", "failed"):
                    return True
            except json.JSONDecodeError:
                return True
    return False


def run_preflight(repo_root: Path | None = None, target_root: Path | None = None) -> PreflightResult:
    """Run non-mutating preflight checks and return findings."""
    home = os.environ.get("HOME")
    env: dict[str, Any] = {
        "os": os.name,
        "platform": sys.platform,
        "architecture": _detect_architecture(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "home": home,
        "prefix": os.environ.get("PREFIX"),
        "tmpdir": os.environ.get("TMPDIR"),
        "termux_version": os.environ.get("TERMUX_VERSION"),
        "hive_home": os.environ.get("HIVE_HOME"),
    }

    classification: dict[str, CapabilityState] = {
        "bash": _command_exists("bash"),
        "git": _command_exists("git"),
        "python": CapabilityState.AVAILABLE,
        "termux": _detect_termux(env),
        "android": CapabilityState.UNVERIFIED,  # Requires physical check.
        "storage": CapabilityState.UNKNOWN,
    }

    errors: list[str] = []
    warnings: list[str] = []

    if not home and target_root is None:
        errors.append("HOME is not set")

    if classification["termux"] == CapabilityState.AVAILABLE and not env["prefix"]:
        warnings.append("Termux detected but PREFIX is not set")

    if resolve_repository_root is None:
        errors.append("lib/hive_path.py is not importable; cannot validate repository identity")
    else:
        try:
            if repo_root is None:
                repo_root = resolve_repository_root()
            env["repository_root"] = str(repo_root)
            env["canonical_source"] = str(resolve_canonical_source(repo_root))
            env["hive_canonical_json"] = str(repo_root / "hive-canonical.json")
        except Exception as e:
            errors.append(f"Repository resolution failed: {e}")

    # Target root determination. Missing HOME is a hard preflight error; use an
    # inert absolute placeholder only so the remainder of this read-only report
    # can be generated without ever selecting a shared temporary directory.
    if target_root is None:
        if home:
            target_root = Path(home) / ".local" / "share" / "hive"
        else:
            errors.append("Cannot determine target root: HOME is not set")
            target_root = Path.cwd().resolve() / ".hive-unresolved-target"
    env["target_root"] = str(target_root)

    existing_status, existing_warnings = _detect_existing_installation(target_root, os.environ)
    warnings.extend(existing_warnings)

    if home:
        state_root = Path(home) / ".local" / "state" / "hive"
        if _detect_incomplete_transaction(state_root):
            warnings.append("Incomplete installation transaction detected")
            if existing_status == InstallStatus.CLEAN_INSTALL:
                existing_status = InstallStatus.RECOVERY_REQUIRED

    # Relative target rejection
    if not target_root.is_absolute():
        errors.append("Target root must be absolute")

    # Shared-storage rejection (POSIX paths only)
    if os.name != "nt" and target_root.parts and str(target_root).startswith(("/sdcard", "/storage", "/mnt")):
        errors.append("Target must not be on shared Android storage")

    # Root path rejection (POSIX paths only)
    if os.name != "nt" and str(target_root).startswith("/root"):
        errors.append("Target must not be under /root")

    return PreflightResult(env, classification, existing_status, warnings, errors)