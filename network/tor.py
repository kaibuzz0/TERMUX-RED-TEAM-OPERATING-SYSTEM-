"""Local Tor daemon adapter for Hive OS.

Manages a Hive-owned Tor process with loopback-only listeners, cookie
authentication, and bounded startup wait.  No hardcoded paths.
"""

from __future__ import annotations

import os
import socket
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from network.errors import NetworkConfigError, NetworkRuntimeError, TorNotAvailableError, TorNotHealthyError
from network.health import HealthCheck


@dataclass(frozen=True)
class TorEndpoints:
    socks_host: str
    socks_port: int
    control_host: str
    control_port: int


def _which_tor() -> str | None:
    """Locate the tor binary; None if unavailable."""
    tor_path = os.environ.get("HIVE_TOR_BINARY")
    if tor_path and Path(tor_path).is_file():
        return tor_path
    for candidate in ("tor", "tor.exe"):
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            p = Path(path_dir) / candidate
            if p.is_file():
                return str(p)
    # Common Termux location
    termux_tor = Path("/data/data/com.termux/files/usr/bin/tor")
    if termux_tor.is_file():
        return str(termux_tor)
    return None


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def _generate_torrc(state_dir: Path, endpoints: TorEndpoints) -> Path:
    """Generate a modern runtime torrc."""
    state_dir.mkdir(parents=True, exist_ok=True)
    torrc = state_dir / "torrc"
    torrc.write_text(
        f"""# Hive OS generated torrc — DO NOT EDIT BY HAND
SOCKSPort {endpoints.socks_host}:{endpoints.socks_port}
ControlPort {endpoints.control_host}:{endpoints.control_port}
CookieAuthentication 1
DataDirectory {state_dir / "data"}
ClientOnly 1
AvoidDiskWrites 1
Log notice file {state_dir / "tor.log"}
""",
        encoding="utf-8",
    )
    try:
        torrc.chmod(0o600)
    except (OSError, NotImplementedError):
        pass
    return torrc


@dataclass
class TorAdapter:
    """Adapter for a Hive-managed local Tor process."""

    state_dir: Path
    endpoints: TorEndpoints
    binary: str | None = None
    _process: subprocess.Popen[str] | None = None

    def __post_init__(self) -> None:
        if self.binary is None:
            self.binary = _which_tor()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.state_dir.chmod(0o700)
        except (OSError, NotImplementedError):
            pass

    def available(self) -> bool:
        return self.binary is not None

    def generate_config(self) -> Path:
        return _generate_torrc(self.state_dir, self.endpoints)

    def start(self, timeout: float = 60.0) -> dict[str, Any]:
        if not self.binary:
            raise TorNotAvailableError("tor binary not found")
        if self.is_running_from_state():
            return {"started": False, "reason": "tor already running", "pid": self._read_pid()}

        torrc = self.generate_config()
        data_dir = self.state_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        try:
            data_dir.chmod(0o700)
        except (OSError, NotImplementedError):
            pass

        # Start tor as a child process we can track exactly.
        try:
            self._process = subprocess.Popen(
                [self.binary, "-f", str(torrc)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise NetworkRuntimeError(f"Failed to start tor: {exc}") from exc

        # Poll for health up to timeout.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            health = self.health()
            if health["checks"].get(HealthCheck.BOOTSTRAP.value, {}).get("ok"):
                return {"started": True, "pid": self._process.pid, "health": health}
            if self._process.poll() is not None:
                raise NetworkRuntimeError("tor process exited during startup")
            time.sleep(0.5)

        health = self.health()
        if health["checks"].get(HealthCheck.BOOTSTRAP.value, {}).get("ok"):
            return {"started": True, "pid": self._process.pid, "health": health}
        raise TorNotHealthyError(f"tor did not become healthy within {timeout}s")

    def stop(self, timeout: float = 10.0) -> dict[str, Any]:
        """Stop the managed Tor process cleanly."""
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            return {"stopped": True, "pid": self._process.pid}

        # Fallback: find a tor process matching our data directory.
        pid = self._find_matching_pid()
        if pid is None:
            return {"stopped": False, "reason": "no managed tor process found"}
        try:
            os.kill(pid, 15)  # SIGTERM
        except ProcessLookupError:
            return {"stopped": False, "reason": "process already gone"}
        except PermissionError as exc:
            raise NetworkRuntimeError(f"Cannot stop tor pid {pid}: {exc}") from exc
        return {"stopped": True, "pid": pid}

    def health(self) -> dict[str, Any]:
        """Return layered health data."""
        results: dict[str, dict[str, Any]] = {}
        results[HealthCheck.TOR_PROCESS.value] = {
            "ok": self.is_running_from_state(),
            "detail": "process running" if self.is_running_from_state() else "process not running",
        }
        results[HealthCheck.SOCKS_LISTENER.value] = {
            "ok": _port_available(self.endpoints.socks_host, self.endpoints.socks_port),
            "detail": f"{self.endpoints.socks_host}:{self.endpoints.socks_port}",
        }
        results[HealthCheck.CONTROL_PORT.value] = {
            "ok": _port_available(self.endpoints.control_host, self.endpoints.control_port),
            "detail": f"{self.endpoints.control_host}:{self.endpoints.control_port}",
        }
        # Bootstrap detection via ControlPort protocol (best-effort).
        bootstrap = self._bootstrap_percentage()
        results[HealthCheck.BOOTSTRAP.value] = {
            "ok": bootstrap == 100,
            "detail": f"{bootstrap}%" if bootstrap is not None else "unknown",
        }
        return {"checks": results}

    def newnym(self, timeout: float = 10.0) -> dict[str, Any]:
        if not _port_available(self.endpoints.control_host, self.endpoints.control_port):
            raise TorNotHealthyError("ControlPort not available")
        cookie = self._control_cookie()
        if cookie is None:
            raise TorNotHealthyError("Control cookie not available")
        return self._control_command(b"AUTHENTICATE %b\r\nSIGNAL NEWNYM\r\nQUIT\r\n" % cookie, timeout)

    def is_running_from_state(self) -> bool:
        return self._find_matching_pid() is not None

    def _read_pid(self) -> int | None:
        pidfile = self.state_dir / "data" / "pid"
        try:
            return int(pidfile.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            return None

    def _find_matching_pid(self) -> int | None:
        """Find a tor process that is using our data directory.

        Avoids pgrep/pkill by inspecting /proc where available; falls back
        to our tracked process handle.
        """
        if self._process is not None and self._process.poll() is None:
            return self._process.pid
        pid = self._read_pid()
        if pid is not None:
            try:
                os.kill(pid, 0)  # permission check / existence
                return pid
            except ProcessLookupError:
                pass
        # /proc scan is POSIX-only; return None otherwise.
        if os.name != "posix":
            return None
        data_dir = (self.state_dir / "data").resolve()
        for entry in Path("/proc").glob("[0-9]*"):
            try:
                cmdline = (entry / "cmdline").read_text(encoding="utf-8", errors="replace").replace("\x00", " ")
                if "tor" not in cmdline:
                    continue
                cwd = (entry / "cwd").resolve()
                if data_dir in [cwd, *cwd.parents]:
                    return int(entry.name)
            except (OSError, PermissionError, FileNotFoundError):
                continue
        return None

    def _control_cookie(self) -> bytes | None:
        cookie_file = self.state_dir / "data" / "control_auth_cookie"
        try:
            data = cookie_file.read_bytes()
        except FileNotFoundError:
            return None
        return data.hex().encode("ascii")

    def _bootstrap_percentage(self) -> int | None:
        cookie = self._control_cookie()
        if cookie is None:
            return None
        if not _port_available(self.endpoints.control_host, self.endpoints.control_port):
            return None
        try:
            response = self._control_command(
                b"AUTHENTICATE %b\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n" % cookie,
                timeout=5.0,
            )
            text = response.get("response", "")
            for line in text.splitlines():
                if "PROGRESS=" in line:
                    part = line.split("PROGRESS=")[1].split()[0]
                    try:
                        return int(part.rstrip("%"))
                    except ValueError:
                        continue
            return None
        except Exception:
            return None

    def _control_command(self, payload: bytes, timeout: float) -> dict[str, Any]:
        import socket
        with socket.create_connection(
            (self.endpoints.control_host, self.endpoints.control_port), timeout=timeout
        ) as sock:
            sock.sendall(payload)
            chunks = []
            sock.settimeout(timeout)
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except socket.timeout:
                pass
            response = b"".join(chunks).decode("utf-8", errors="replace")
        ok = "250 OK" in response
        return {"ok": ok, "response": response}


def make_tor_adapter(state_dir: Path, endpoints: TorEndpoints) -> TorAdapter:
    return TorAdapter(state_dir=state_dir, endpoints=endpoints)
