"""Health checks for managed services."""

from __future__ import annotations

import http.client
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


class HealthCheck:
    """Run configured health checks safely."""

    def __init__(self, manifest: dict[str, Any]):
        self.config = manifest.get("health_check", {})
        self.type = self.config.get("type", "process")

    def check(self, process: Any, log_root: Path) -> dict[str, Any]:
        if self.type == "none":
            return {"healthy": True, "type": "none"}
        if self.type == "process":
            return {"healthy": process.is_running() if process else False, "type": "process"}
        if self.type == "command":
            return self._command_check()
        if self.type == "tcp-local":
            return self._tcp_check()
        if self.type == "http-local":
            return self._http_check()
        if self.type == "file":
            return self._file_check(log_root)
        return {"healthy": False, "type": self.type, "error": "Unsupported"}

    def _command_check(self) -> dict[str, Any]:
        args = self.config.get("args", [])
        timeout = self.config.get("timeout_seconds", 5)
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)
            return {"healthy": result.returncode == 0, "type": "command", "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"healthy": False, "type": "command", "error": "timeout"}
        except Exception as e:
            return {"healthy": False, "type": "command", "error": str(e)}

    def _tcp_check(self) -> dict[str, Any]:
        host = self.config.get("host", "127.0.0.1")
        port = self.config.get("port")
        timeout = self.config.get("timeout_seconds", 5)
        if host not in {"127.0.0.1", "::1", "localhost"}:
            return {"healthy": False, "type": "tcp-local", "error": f"Non-loopback host rejected: {host}"}
        if not isinstance(port, int) or port <= 0 or port > 65535:
            return {"healthy": False, "type": "tcp-local", "error": f"Invalid port: {port}"}
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return {"healthy": True, "type": "tcp-local"}
        except OSError:
            return {"healthy": False, "type": "tcp-local"}

    def _http_check(self) -> dict[str, Any]:
        host = self.config.get("host", "127.0.0.1")
        port = self.config.get("port")
        path = self.config.get("path", "/")
        timeout = self.config.get("timeout_seconds", 5)
        if host not in {"127.0.0.1", "::1", "localhost"}:
            return {"healthy": False, "type": "http-local", "error": f"Non-loopback host rejected: {host}"}
        if not isinstance(port, int) or port <= 0 or port > 65535:
            return {"healthy": False, "type": "http-local", "error": f"Invalid port: {port}"}
        if not isinstance(path, str) or not path.startswith("/") or "\r" in path or "\n" in path:
            return {"healthy": False, "type": "http-local", "error": "Invalid HTTP path"}

        connection = http.client.HTTPConnection(host, port, timeout=timeout)
        try:
            connection.request("GET", path, headers={"User-Agent": "Hive-OS/1.1"})
            response = connection.getresponse()
            _ = response.read()
            healthy = 200 <= response.status < 400
            result = {"healthy": healthy, "type": "http-local", "status": response.status}
            if not healthy:
                result["error"] = f"HTTP status {response.status}"
            return result
        except Exception as e:
            return {"healthy": False, "type": "http-local", "error": str(e)}
        finally:
            connection.close()

    def _file_check(self, log_root: Path) -> dict[str, Any]:
        rel = self.config.get("path")
        if not isinstance(rel, str):
            return {"healthy": False, "type": "file", "error": "missing path"}
        target = log_root / rel
        try:
            target.relative_to(log_root)
        except ValueError:
            return {"healthy": False, "type": "file", "error": "path escapes log root"}
        if not target.exists():
            return {"healthy": False, "type": "file", "error": "missing"}
        freshness = self.config.get("freshness_seconds")
        if freshness:
            age = time.time() - target.stat().st_mtime
            if age > freshness:
                return {"healthy": False, "type": "file", "error": f"stale ({age:.0f}s)"}
        return {"healthy": True, "type": "file"}
