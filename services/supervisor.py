"""Native service supervisor: start, stop, restart, status."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from services.errors import ServiceConfigError, ServiceRuntimeError, ServiceStateError
from services.graph import DependencyGraph
from services.health import HealthCheck
from services.logging import resolve_log_targets
from services.process import TrackedProcess, _command_digest, _manifest_digest
from services.restart import RestartPolicy
from services.state import ServiceInstance, atomic_write_json, load_state, save_state


def _repo_root() -> Path:
    from lib.hive_path import resolve_repository_root_from_file
    return resolve_repository_root_from_file(__file__)


class Supervisor:
    """Manages service lifecycle without enabling auto-start."""

    def __init__(
        self,
        manifests: dict[str, dict[str, Any]],
        state_root: Path,
        log_root: Path,
        runtime_info: dict[str, Any],
    ):
        self.manifests = manifests
        self.state_root = state_root
        self.log_root = log_root
        self.runtime_info = runtime_info
        self.graph = DependencyGraph(manifests)
        self.policies: dict[str, RestartPolicy] = {n: RestartPolicy(m) for n, m in manifests.items()}
        self.processes: dict[str, TrackedProcess] = {}
        self._load_instances()

    def _load_instances(self) -> None:
        raw = load_state(self.state_root)
        for name, data in raw.items():
            self.processes[name] = None  # placeholder; runtime processes re-bound on demand

    def _resolve_path(self, base: str | None, rel: str, manifest: dict[str, Any]) -> Path:
        from lib.hive_path import (
            resolve_canonical_source,
            resolve_config_root,
            resolve_data_root,
            resolve_cache_root,
            resolve_log_root,
            resolve_state_root,
            resolve_repository_root,
        )
        repo_root = _repo_root()
        if base is None or base == "repository":
            root = repo_root
        elif base == "canonical-source":
            root = resolve_canonical_source(repo_root)
        elif base == "config-root":
            root = resolve_config_root()
        elif base == "state-root":
            root = resolve_state_root()
        elif base == "data-root":
            root = resolve_data_root()
        elif base == "cache-root":
            root = resolve_cache_root()
        elif base == "log-root":
            root = resolve_log_root()
        elif base == "temp-root":
            root = Path(tempfile.gettempdir()) / "hive"
        elif base == "active-runtime":
            root = self.state_root / "active-runtime"
        else:
            raise ServiceConfigError(f"Unknown path base: {base}")
        target = (root / rel).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            raise ServiceConfigError(f"Path escapes base: {rel}")
        return target

    def _resolve_command(self, manifest: dict[str, Any]) -> list[str]:
        cmd_cfg = manifest.get("command", {})
        interpreter = cmd_cfg.get("interpreter")
        base = cmd_cfg.get("base")
        rel = cmd_cfg.get("path", "")
        args = list(cmd_cfg.get("args", []))
        target = self._resolve_path(base, rel, manifest) if rel else None
        prefix: list[str] = []
        if interpreter == "python":
            prefix = [sys.executable]
        elif interpreter == "bash":
            exe = shutil.which("bash")
            if not exe:
                raise ServiceRuntimeError("bash interpreter not available")
            prefix = [exe]
        elif interpreter == "sh":
            exe = shutil.which("sh")
            if not exe:
                raise ServiceRuntimeError("sh interpreter not available")
            prefix = [exe]
        if target:
            prefix.append(str(target))
        return prefix + args

    def _build_environment(self, manifest: dict[str, Any]) -> dict[str, str]:
        env_cfg = manifest.get("environment", {})
        allow = env_cfg.get("allow", [])
        sets = env_cfg.get("set", {})
        env: dict[str, str] = {}
        for name in allow:
            if name in os.environ:
                env[name] = os.environ[name]
        env.update(sets)
        return env

    def start(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        if not manifest.get("enabled", False):
            raise ServiceRuntimeError(f"Service {name} is disabled")
        # dependency validation
        for dep in manifest.get("dependencies", []):
            if not self._is_running(dep):
                raise ServiceRuntimeError(f"Dependency {dep} of {name} is not running")
        if self._is_running(name):
            return {"service": name, "state": "RUNNING", "pid": self.processes[name].pid}
        cmd = self._resolve_command(manifest)
        cwd_cfg = manifest.get("working_directory", {})
        cwd = self._resolve_path(cwd_cfg.get("base"), cwd_cfg.get("path", "."), manifest)
        env = self._build_environment(manifest)
        session_id = self._session_id()
        proc = TrackedProcess(manifest, cmd, session_id)
        stdout, stderr = resolve_log_targets(manifest, self.log_root)
        if stdout:
            stdout.parent.mkdir(parents=True, exist_ok=True)
        if stderr:
            stderr.parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"cwd": str(cwd), "env": env, "start_new_session": True}
        if stdout:
            kwargs["stdout"] = open(stdout, "a")
        if stderr:
            kwargs["stderr"] = open(stderr, "a")
        try:
            # Re-create Popen directly to manage file handles.
            import subprocess
            proc._proc = subprocess.Popen(cmd, **kwargs)
        except OSError as e:
            raise ServiceRuntimeError(f"Failed to start {name}: {e}") from e
        proc.start_time = time.time()
        self.processes[name] = proc
        self._record(name, state="RUNNING", pid=proc.pid, session_id=session_id, command_digest=_command_digest(cmd), manifest_digest=_manifest_digest(manifest))
        # startup health check
        hc = HealthCheck(manifest)
        for _ in range(manifest.get("health_check", {}).get("failure_threshold", 3)):
            result = hc.check(proc, self.log_root)
            if result["healthy"]:
                self._record(name, last_health_status="healthy")
                return {"service": name, "state": "RUNNING", "pid": proc.pid}
            time.sleep(manifest.get("health_check", {}).get("interval_seconds", 1))
        self._record(name, state="FAILED", last_health_status="unhealthy")
        return {"service": name, "state": "FAILED"}

    def stop(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        proc = self.processes.get(name)
        if proc is None or not proc.is_running():
            return {"service": name, "state": "STOPPED"}
        shutdown = manifest.get("shutdown", {})
        signal_name = shutdown.get("signal", "TERM")
        timeout = shutdown.get("timeout_seconds", 10)
        kill_after = shutdown.get("kill_after_timeout", True)
        result = proc.terminate(signal_name, timeout, kill_after)
        if not result["signaled"] and result.get("reason") == "process identity unverified":
            self._record(name, state="UNVERIFIED", last_error="process identity unverified; stop aborted")
            return {"service": name, "state": "UNVERIFIED", "reason": "process identity unverified"}
        self._record(name, state="STOPPED", last_exit_code=result.get("exit_code"), stop_timestamp=self._now())
        return {"service": name, "state": "STOPPED", "exit_code": result.get("exit_code")}

    def restart(self, name: str) -> dict[str, Any]:
        self.stop(name)
        return self.start(name)

    def status(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        proc = self.processes.get(name)
        running = proc.is_running() if proc else False
        return {
            "service": name,
            "enabled": manifest.get("enabled", False),
            "state": "RUNNING" if running else "STOPPED",
            "pid": proc.pid if running else None,
        }

    def health(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        proc = self.processes.get(name)
        hc = HealthCheck(manifest)
        return hc.check(proc, self.log_root)

    def reset(self, name: str) -> dict[str, Any]:
        self._manifest(name)
        policy = self.policies.setdefault(name, RestartPolicy(self.manifests[name]))
        policy.reset(name)
        self._record(name, state="DEFINED", restart_count=0)
        return {"service": name, "state": "RESET"}

    def _manifest(self, name: str) -> dict[str, Any]:
        if name not in self.manifests:
            raise ServiceConfigError(f"Unknown service: {name}")
        return self.manifests[name]

    def _is_running(self, name: str) -> bool:
        proc = self.processes.get(name)
        return proc.is_running() if proc else False

    def _record(self, name: str, **kwargs: Any) -> None:
        state = load_state(self.state_root)
        entry = state.setdefault(name, ServiceInstance(service_name=name).to_dict())
        entry.update(kwargs)
        save_state(self.state_root, state)

    def _session_id(self) -> str:
        return f"{time.time():.6f}-{os.getpid()}"

    def _now(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
