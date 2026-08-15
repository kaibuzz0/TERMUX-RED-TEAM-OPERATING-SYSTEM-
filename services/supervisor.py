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

from network import NetworkManager
from network.health import HealthLevel
from network.profiles import NetworkProfile
from services.errors import ServiceConfigError, ServiceRuntimeError, ServiceStateError
from services.graph import DependencyGraph
from runtime_logs.service_logger import RuntimeLogger, ServiceLogger
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
        network_manager: NetworkManager | None = None,
    ):
        self.manifests = manifests
        self.state_root = state_root
        self.log_root = log_root
        self.runtime_info = runtime_info
        self.network_manager = network_manager
        self.graph = DependencyGraph(manifests)
        self.policies: dict[str, RestartPolicy] = {n: RestartPolicy(m) for n, m in manifests.items()}
        self.processes: dict[str, TrackedProcess] = {}
        self._service_loggers: dict[str, ServiceLogger] = {}
        self._runtime_logger = RuntimeLogger(log_root, "supervisor")
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

    def _network_eligibility(self, name: str) -> tuple[bool, str]:
        """Check whether current network state satisfies the service's network requirement."""
        manifest = self._manifest(name)
        network = manifest.get("network", {})
        if not network.get("required", False):
            return True, "no network requirement"
        if self.network_manager is None:
            return False, "network manager not available"
        required_profile = network.get("profile")
        if required_profile is not None and required_profile == "any":
            required_profile = None
        ok, reason = self.network_manager.requirement_satisfied(
            network_required=True,
            required_profile=required_profile,
        )
        return ok, reason

    def start(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        if not manifest.get("enabled", False):
            raise ServiceRuntimeError(f"Service {name} is disabled")
        # network eligibility
        net_ok, net_reason = self._network_eligibility(name)
        if not net_ok:
            self._record(name, state="BLOCKED_NETWORK", last_error=net_reason)
            return {"service": name, "state": "BLOCKED_NETWORK", "reason": net_reason}
        # dependency validation
        for dep in manifest.get("dependencies", []):
            if not self._is_running(dep):
                self._record(name, state="BLOCKED_DEPENDENCY", last_error=f"Dependency {dep} not running")
                return {"service": name, "state": "BLOCKED_DEPENDENCY", "reason": f"Dependency {dep} not running"}
        if self._is_running(name):
            return {"service": name, "state": "RUNNING", "pid": self.processes[name].pid}
        cmd = self._resolve_command(manifest)
        cwd_cfg = manifest.get("working_directory", {})
        cwd = self._resolve_path(cwd_cfg.get("base"), cwd_cfg.get("path", "."), manifest)
        env = self._build_environment(manifest)
        # Inject Hive proxy environment when the service requests it and current profile allows.
        if self.network_manager is not None and manifest.get("network", {}).get("use_proxy_env", False):
            net_ok, _ = self._network_eligibility(name)
            if net_ok:
                env = self.network_manager.proxy_env()
        session_id = self._session_id()
        proc = TrackedProcess(manifest, cmd, session_id)
        # Use canonical service logger for bounded, rotated stdout/stderr.
        svc_logger = ServiceLogger(name, self.log_root)
        handles = svc_logger.open_handles()
        try:
            import subprocess
            proc._proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=handles["stdout"],
                stderr=handles["stderr"],
                start_new_session=True,
            )
        except OSError as e:
            svc_logger.close()
            raise ServiceRuntimeError(f"Failed to start {name}: {e}") from e
        self._service_loggers[name] = svc_logger
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

    def status(self, name: str | None = None) -> dict[str, Any]:
        if name is not None:
            return self._single_status(name)
        # Global status
        services = {}
        for name in sorted(self.manifests):
            services[name] = self._single_status(name)
        network = self._network_summary()
        return {
            "supervisor": "active",
            "services_configured": len(self.manifests),
            "services_running": sum(1 for s in services.values() if s["state"] == "RUNNING"),
            "services_blocked": sum(1 for s in services.values() if s["state"].startswith("BLOCKED")),
            "services_failed": sum(1 for s in services.values() if s["state"] == "FAILED"),
            "network": network,
            "services": services,
        }

    def _single_status(self, name: str) -> dict[str, Any]:
        manifest = self._manifest(name)
        proc = self.processes.get(name)
        running = proc.is_running() if proc else False
        state = self._load_instance_state(name)
        actual_state = "RUNNING" if running else state.get("state", "STOPPED")
        return {
            "service": name,
            "enabled": manifest.get("enabled", False),
            "state": actual_state,
            "pid": proc.pid if running else None,
            "restart_count": state.get("restart_count", 0),
            "last_health": state.get("last_health_status"),
            "last_error": state.get("last_error"),
            "network_required": manifest.get("network", {}).get("required", False),
        }

    def _network_summary(self) -> dict[str, Any] | None:
        if self.network_manager is None:
            return None
        report = self.network_manager.health()
        return {
            "profile": self.network_manager.current_profile.name,
            "overall": report.overall,
        }

    def _load_instance_state(self, name: str) -> dict[str, Any]:
        raw = load_state(self.state_root)
        return raw.get(name, {})

    def health(self, name: str | None = None) -> dict[str, Any]:
        if name is None:
            results = {}
            for svc in sorted(self.manifests):
                results[svc] = self.health(svc)
            return results
        manifest = self._manifest(name)
        proc = self.processes.get(name)
        hc = HealthCheck(manifest)
        return hc.check(proc, self.log_root)

    def ensure(self) -> dict[str, Any]:
        """Start all eligible, enabled services in dependency order."""
        started = []
        blocked = []
        for name in self.graph.order():
            manifest = self.manifests.get(name, {})
            if not manifest.get("enabled", False):
                continue
            net_ok, reason = self._network_eligibility(name)
            if not net_ok:
                self._record(name, state="BLOCKED_NETWORK", last_error=reason)
                blocked.append({"service": name, "reason": reason})
                continue
            if self._is_running(name):
                started.append({"service": name, "state": "RUNNING"})
                continue
            try:
                result = self.start(name)
                started.append(result)
            except ServiceRuntimeError as exc:
                self._record(name, state="FAILED", last_error=str(exc))
                blocked.append({"service": name, "reason": str(exc)})
        return {"started": started, "blocked": blocked}

    def ps(self) -> list[dict[str, Any]]:
        """Return Hive-owned processes."""
        rows = []
        for name in sorted(self.manifests):
            proc = self.processes.get(name)
            state = self._load_instance_state(name)
            if proc and proc.is_running():
                uptime = None
                if proc.start_time:
                    uptime = time.time() - proc.start_time
                rows.append({
                    "service": name,
                    "pid": proc.pid,
                    "state": "RUNNING",
                    "uptime_seconds": uptime,
                    "restart_count": state.get("restart_count", 0),
                    "health": state.get("last_health_status"),
                    "network_required": self.manifests[name].get("network", {}).get("required", False),
                })
        return rows

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
        self._runtime_logger.write(
            "SERVICE_STATE_CHANGE",
            f"Service {name} state update",
            {"service": name, "updates": kwargs},
        )

    def _session_id(self) -> str:
        return f"{time.time():.6f}-{os.getpid()}"

    def _now(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
