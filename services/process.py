"""Process identity, tracking, and safe signaling."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from services.errors import ServiceRuntimeError


def _digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()[:16]


def _manifest_digest(manifest: dict[str, Any]) -> str:
    return _digest(manifest)


def _command_digest(command: list[str]) -> str:
    return hashlib.sha256(json.dumps(command, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def _process_start_time(pid: int) -> float | None:
    """Return a process start-time identity value from the host OS."""
    try:
        if sys.platform == "win32":
            import psutil  # type: ignore
            return psutil.Process(pid).create_time()
        stat_path = Path(f"/proc/{pid}/stat")
        if not stat_path.exists():
            return None
        parts = stat_path.read_text().split()
        # Linux /proc starttime is clock ticks since boot. Keep that native
        # representation (converted to seconds) and compare like with like.
        return float(parts[21]) / os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    except Exception:
        return None


def _cmdline(pid: int) -> list[str] | None:
    try:
        if sys.platform == "win32":
            import psutil  # type: ignore
            return psutil.Process(pid).cmdline()
        cmd_path = Path(f"/proc/{pid}/cmdline")
        if not cmd_path.exists():
            return None
        return cmd_path.read_bytes().decode("utf-8", errors="replace").split("\x00")
    except Exception:
        return None


class TrackedProcess:
    """Wraps a managed subprocess and validates its identity."""

    def __init__(self, manifest: dict[str, Any], command: list[str], session_id: str):
        self.manifest = manifest
        self.command = command
        self.session_id = session_id
        self.manifest_digest = _manifest_digest(manifest)
        self.command_digest = _command_digest(command)
        self._proc: subprocess.Popen | None = None
        self.start_time: float | None = None

    def start(self, cwd: Path, env: dict[str, str]) -> None:
        try:
            kwargs: dict[str, Any] = {
                "cwd": str(cwd),
                "env": env,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "start_new_session": True,
            }
            self._proc = subprocess.Popen(self.command, **kwargs)
        except OSError as e:
            raise ServiceRuntimeError(f"Failed to start service: {e}") from e
        # Store the same OS-derived start-time value used during validation.
        # Falling back to wall time is safe only on platforms where the helper
        # itself also reports wall time (Windows); on Linux an unavailable
        # /proc value remains None and command/Popen identity still applies.
        observed = _process_start_time(self._proc.pid)
        if observed is not None:
            self.start_time = observed
        elif sys.platform == "win32":
            self.start_time = time.time()
        else:
            self.start_time = None

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    def poll(self) -> int | None:
        if self._proc is None:
            return None
        return self._proc.poll()

    def is_running(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def validate_identity(self, pid: int | None = None) -> bool:
        pid = pid or self.pid
        if pid is None:
            return False
        if not self.is_running():
            return False
        start = _process_start_time(pid)
        if start is not None and self.start_time is not None and abs(start - self.start_time) > 5:
            return False
        cmdline = _cmdline(pid)
        if cmdline and self.command:
            # Accept if one of the executable-related command parts is present.
            joined = " ".join(cmdline)
            return any(part in joined for part in self.command[:2])
        return True

    def _signal_if_identity_valid(self, sig: int) -> bool:
        if not self.validate_identity():
            return False
        try:
            os.kill(self._proc.pid, sig)
            return True
        except ProcessLookupError:
            return False

    def terminate(self, signal_name: str, timeout: float, kill_after_timeout: bool) -> dict[str, Any]:
        if self._proc is None:
            return {"signaled": False, "exit_code": None, "reason": "no process"}
        if self._proc.poll() is not None:
            return {"signaled": False, "exit_code": self._proc.poll(), "reason": "already exited"}
        sig = getattr(signal, signal_name, signal.SIGTERM)
        if not self._signal_if_identity_valid(sig):
            return {"signaled": False, "exit_code": None, "reason": "process identity unverified"}
        deadline = time.time() + timeout
        while time.time() < deadline:
            code = self._proc.poll()
            if code is not None:
                return {"signaled": True, "exit_code": code}
            time.sleep(0.1)
        if kill_after_timeout:
            if not self._signal_if_identity_valid(signal.SIGKILL):
                return {"signaled": True, "exit_code": None, "reason": "escalation aborted: identity unverified"}
            try:
                return {"signaled": True, "exit_code": self._proc.wait(timeout=5)}
            except subprocess.TimeoutExpired:
                return {"signaled": True, "exit_code": None, "reason": "kill did not complete"}
        return {"signaled": True, "exit_code": None, "reason": "graceful timeout"}
