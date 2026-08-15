"""CLI surface for `hive health`, `hive doctor`, `hive audit`, `hive selftest`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from config_engine import get_config
from diagnostics import diagnose, evaluate_health, run_audit, run_selftest
from diagnostics.finding import Finding
from diagnostics.severity import Severity
from network import NetworkManager
from services.registry import ServiceRegistry
from services.supervisor import Supervisor


def _repo_root() -> Path:
    from lib.hive_path import resolve_repository_root_from_file
    return resolve_repository_root_from_file(__file__)


def _make_network_manager() -> NetworkManager:
    runtime = get_config("runtime")
    return NetworkManager(state_root=Path(runtime["state_root"]), repo_root=_repo_root())


def _make_supervisor() -> Supervisor:
    from config_engine import get_config
    svc_cfg = get_config("services")
    runtime_cfg = get_config("runtime")
    repo_root = _repo_root()
    registry = ServiceRegistry(repo_root, Path(svc_cfg["state_root"]))
    registry.load([Path(d) for d in svc_cfg.get("manifest_dirs", [])])
    network_manager = NetworkManager(state_root=Path(runtime_cfg["state_root"]), repo_root=repo_root)
    return Supervisor(
        registry.native,
        Path(svc_cfg["state_root"]),
        Path(svc_cfg["log_root"]),
        {},
        network_manager=network_manager,
    )


def _print_json(data: dict[str, Any]) -> None:
    import json
    print(json.dumps(data, indent=2, default=str))


def _findings_to_dict(findings: list[Finding]) -> list[dict[str, Any]]:
    return [f.to_dict() for f in findings]


def cmd_health(args: argparse.Namespace) -> int:
    net_mgr = _make_network_manager()
    sup = _make_supervisor()
    report = evaluate_health(net_mgr, sup, broker_available=True, vault_state="LOCKED")
    if args.json:
        _print_json(report.to_dict())
    else:
        print(f"Hive Health: {report.overall.upper()}")
        for comp, state in report.components.items():
            print(f"  {comp}: {state}")
        for f in report.findings:
            print(f"  [{f.severity.value}] {f.code}: {f.message}")
    if report.overall == "healthy":
        return 0
    if report.overall == "degraded":
        return 1
    return 2


def cmd_doctor(args: argparse.Namespace) -> int:
    net_mgr = _make_network_manager()
    sup = _make_supervisor()
    runtime = get_config("runtime")
    findings = diagnose(
        net_mgr,
        sup,
        repo_root=_repo_root(),
        state_root=Path(runtime["state_root"]),
        log_root=Path(runtime["log_root"]),
        vault_state="LOCKED",
    )
    if args.json:
        _print_json({"findings": _findings_to_dict(findings)})
    else:
        if not findings:
            print("No issues found.")
            return 0
        print(f"Doctor found {len(findings)} finding(s):")
        for f in findings:
            print(f"  [{f.severity.value}] {f.code} ({f.component}): {f.message}")
            if f.remediation:
                print(f"    -> {f.remediation}")
    severities = [f.severity for f in findings]
    if any(s == Severity.CRITICAL for s in severities):
        return 2
    if any(s in (Severity.ERROR, Severity.WARNING) for s in severities):
        return 1
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    net_mgr = _make_network_manager()
    sup = _make_supervisor()
    runtime = get_config("runtime")
    repo_root = _repo_root()
    findings = run_audit(
        net_mgr,
        sup,
        repo_root,
        Path(runtime["state_root"]),
        Path(runtime["log_root"]),
    )
    if args.json:
        _print_json({"findings": _findings_to_dict(findings)})
    else:
        if not findings:
            print("Audit: clean")
            return 0
        print(f"Audit found {len(findings)} finding(s):")
        for f in findings:
            print(f"  [{f.severity.value}] {f.code} ({f.component}): {f.message}")
    severities = [f.severity for f in findings]
    if any(s == Severity.CRITICAL for s in severities):
        return 2
    if any(s in (Severity.ERROR, Severity.WARNING) for s in severities):
        return 1
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    net_mgr = _make_network_manager()
    sup = _make_supervisor()
    repo_root = _repo_root()

    steps = []
    if args.network:
        def step_network(mgr, _):
            report = mgr.health()
            if report.level.name == "UNAVAILABLE" and mgr.current_profile != mgr.current_profile.__class__.HOLD:
                raise RuntimeError(f"Network unavailable: {report.overall}")
        steps.append(step_network)
    if args.service:
        def step_service(_, sv):
            status = sv.status()
            if status.get("services_failed", 0) > 0:
                raise RuntimeError("Services failed")
        steps.append(step_service)

    result = run_selftest(net_mgr, sup, repo_root, steps=steps or None)
    if args.json:
        _print_json(result)
    else:
        print(f"Selftest: {result['overall']}")
        for s in result["steps"]:
            print(f"  {s['name']}: {s['result']} ({s['duration_ms']:.1f}ms)")
            if s["error"]:
                print(f"    error: {s['error']}")
        if result["restore_errors"]:
            print("  Restore errors:")
            for e in result["restore_errors"]:
                print(f"    {e}")
    return 0 if result["overall"] == "PASS" and not result["restore_errors"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health", help="Quick read-only health summary")
    p_health.add_argument("--json", action="store_true")
    p_health.set_defaults(func=cmd_health)

    p_doctor = sub.add_parser("doctor", help="Diagnostic findings and remediation suggestions")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=cmd_doctor)

    p_audit = sub.add_parser("audit", help="Read-only security/configuration audit")
    p_audit.add_argument("--json", action="store_true")
    p_audit.set_defaults(func=cmd_audit)

    p_selftest = sub.add_parser("selftest", help="Active integration selftest with state restore")
    p_selftest.add_argument("--json", action="store_true")
    p_selftest.add_argument("--network", action="store_true", default=True)
    p_selftest.add_argument("--service", action="store_true", default=True)
    p_selftest.add_argument("--no-network", dest="network", action="store_false")
    p_selftest.add_argument("--no-service", dest="service", action="store_false")
    p_selftest.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
