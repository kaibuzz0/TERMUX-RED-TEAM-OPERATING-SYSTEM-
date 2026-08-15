"""Subsystem adapters for the broker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from services.cli import main as services_main


class AdapterError(Exception):
    """Subsystem adapter error."""


def _run_services_argv(argv: list[str]) -> dict[str, Any]:
    # Run services CLI in a subprocess to avoid sys.stdout races with the caller's threads.
    cmd = [sys.executable, "-m", "services.cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "services adapter timeout"}


def dispatch(capability: str, txn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a broker capability to the appropriate read-only adapter."""
    if capability == "broker.capabilities":
        from hive_broker.capabilities import get_capabilities
        return {"capabilities": get_capabilities()}
    if capability == "broker.status":
        return {"status": "ok", "transaction_id": txn.transaction_id}
    if capability == "broker.stop":
        return {"status": "stop requested"}
    if capability.startswith("service."):
        return _dispatch_service(capability, params)
    if capability.startswith("vault."):
        return _dispatch_vault(capability, params)
    if capability.startswith("update."):
        return _dispatch_update(capability, params)
    if capability.startswith("recovery."):
        return _dispatch_recovery(capability, params)
    if capability.startswith("network."):
        return _dispatch_network(capability, params)
    if capability.startswith("diagnostics."):
        return _dispatch_diagnostics(capability, params)
    if capability.startswith("logs."):
        return _dispatch_logs(capability, params)
    if capability.startswith("termux."):
        return _dispatch_termux(capability, params)
    raise AdapterError(f"No adapter for capability: {capability}")


def _dispatch_service(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    if capability == "service.list":
        return _services_result(["list"])
    service = params.get("service") or ""
    # Skip per-service calls when no service is specified (zero services configured).
    if capability in ("service.status", "service.health") and not service:
        return {"status": "skipped", "reason": "no service specified"}
    mapping = {
        "service.show": ["show", service],
        "service.status": ["status", service],
        "service.health": ["health", service],
        "service.validate": ["validate"],
        "service.graph": ["graph"],
    }
    if capability in mapping:
        return _services_result(mapping[capability])
    raise AdapterError(f"Unsupported service capability: {capability}")


def _services_result(argv: list[str]) -> dict[str, Any]:
    return _run_services_argv(argv)


def _dispatch_vault(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    if capability == "vault.status":
        # Vault status is not yet exposed as a CLI; return a placeholder.
        return {"status": "locked", "note": "vault secret access is not exposed through the broker"}
    raise AdapterError(f"Unsupported vault capability: {capability}")


def _dispatch_update(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "update.status": ["update", "status"],
        "update.inspect": ["update", "inspect"],
        "update.plan": ["update", "plan"],
        "update.verify": ["update", "verify"],
    }
    if capability in mapping:
        return _run_update_argv(mapping[capability])
    raise AdapterError(f"Unsupported update capability: {capability}")


def _run_update_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "updates.cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "update adapter timeout"}


def _dispatch_recovery(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "recovery.status": ["recovery", "status"],
        "recovery.diagnose": ["recovery", "diagnose"],
        "recovery.inspect": ["recovery", "inspect"],
        "recovery.verify": ["recovery", "verify"],
    }
    if capability in mapping:
        return _run_recovery_argv(mapping[capability])
    raise AdapterError(f"Unsupported recovery capability: {capability}")


def _run_recovery_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "updates.recovery_cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "recovery adapter timeout"}

def _dispatch_network(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    """Read-only network capabilities via network CLI."""
    if capability == "network.status":
        return _run_network_argv(["status", "--json"])
    if capability == "network.health":
        return _run_network_argv(["status", "--json"])
    if capability == "network.profile.read":
        return _run_network_argv(["status", "--json"])
    raise AdapterError(f"Unsupported network capability: {capability}")


def _run_network_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "network.cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "network adapter timeout"}


def _dispatch_diagnostics(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    """Read-only diagnostic capabilities via diagnostics CLI."""
    mapping = {
        "diagnostics.health": ["health", "--json"],
        "diagnostics.doctor": ["doctor", "--json"],
        "diagnostics.audit": ["audit", "--json"],
    }
    if capability in mapping:
        return _run_diagnostics_argv(mapping[capability])
    raise AdapterError(f"Unsupported diagnostics capability: {capability}")


def _run_diagnostics_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "diagnostics.cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "diagnostics adapter timeout"}


def _dispatch_logs(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    """Read-only logging capabilities."""
    if capability == "logs.status":
        return _run_logs_argv(["show", "--status"])
    if capability == "logs.tail":
        service = params.get("service")
        if not service:
            return {"status": "skipped", "reason": "no service specified"}
        return _run_logs_argv(["show", service, "--tail", "50"])
    if capability == "logs.service.read":
        service = params.get("service")
        if not service:
            return {"status": "skipped", "reason": "no service specified"}
        return _run_logs_argv(["show", service])
    raise AdapterError(f"Unsupported logs capability: {capability}")


def _run_logs_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "runtime_logs.cli"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "logs adapter timeout"}


def _dispatch_termux(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    """Read-only Termux integration status."""
    if capability == "termux.integration.status":
        return _run_termux_argv(["status"])
    raise AdapterError(f"Unsupported termux capability: {capability}")


def _run_termux_argv(argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "installer.termux_repair"] + argv
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False, cwd=str(Path.cwd()))
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": "termux adapter timeout"}
