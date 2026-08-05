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
    import io
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        code = services_main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return {"exit_code": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


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
    raise AdapterError(f"No adapter for capability: {capability}")


def _dispatch_service(capability: str, params: dict[str, Any]) -> dict[str, Any]:
    if capability == "service.list":
        return _services_result(["list"])
    service = params.get("service", "")
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
