"""CLI surface for `hive broker *` commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hive_broker import Broker
from hive_broker.errors import BrokerError




def _broker() -> Broker:
    from config_engine import get_config
    runtime = get_config("runtime")
    state_root = Path(runtime["state_root"])
    log_root = Path(runtime["log_root"])
    return Broker(state_root, log_root)


def _load_manifest(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"Manifest not found: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON manifest: {e}")
    if not isinstance(data, dict):
        raise SystemExit("Manifest must be a JSON object")
    return data


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_capabilities(args: argparse.Namespace) -> int:
    broker = _broker()
    _print_json(broker.capabilities())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    broker = _broker()
    raw = _load_manifest(args.manifest)
    _print_json(broker.validate(raw))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    broker = _broker()
    raw = _load_manifest(args.manifest)
    _print_json(broker.inspect(raw))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    broker = _broker()
    raw = _load_manifest(args.manifest)
    try:
        result = broker.run(raw)
        _print_json(result)
        return 0 if result["status"] == "success" else 2
    except BrokerError as e:
        _print_json({"status": "failure", "error": str(e)})
        return 2


def cmd_status(args: argparse.Namespace) -> int:
    broker = _broker()
    _print_json(broker.status())
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    broker = _broker()
    result = broker.stop(args.transaction)
    _print_json(result)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    broker = _broker()
    records = broker.audit.read_transaction(args.transaction)
    _print_json({"records": records})
    return 0


def cmd_policy_check(args):
    """Broker-facing read-only policy check."""
    decision = _check_policy(
        actor_type=args.actor,
        capability=args.capability,
        resource_type=args.resource,
        resource_id=args.resource_id,
    )
    decision["execution_performed"] = False
    _print_json(decision)
    return 0 if decision["decision"] == "ALLOW" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive broker")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("capabilities", help="Show broker capabilities")
    validate_p = sub.add_parser("validate", help="Validate a manifest without executing")
    validate_p.add_argument("--manifest", required=True)
    inspect_p = sub.add_parser("inspect", help="Inspect a manifest and runtime compatibility")
    inspect_p.add_argument("--manifest", required=True)
    run_p = sub.add_parser("run", help="Execute a validated manifest")
    run_p.add_argument("--manifest", required=True)
    sub.add_parser("status", help="Show broker session status")
    stop_p = sub.add_parser("stop", help="Stop broker session or transaction")
    stop_p.add_argument("--transaction", default=None)
    audit_p = sub.add_parser("audit", help="Look up audit records by transaction")
    audit_p.add_argument("--transaction", required=True)
    policy_p = sub.add_parser("policy-check", help="Evaluate a capability through the Policy Engine (read-only check)")
    policy_p.add_argument("capability", help="Capability to evaluate")
    policy_p.add_argument("--actor", default="broker", help="Actor type")
    policy_p.add_argument("--resource", default="service", help="Resource type")
    policy_p.add_argument("--resource-id", default="default", help="Resource ID")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "capabilities": cmd_capabilities,
        "validate": cmd_validate,
        "inspect": cmd_inspect,
        "run": cmd_run,
        "status": cmd_status,
        "stop": cmd_stop,
        "audit": cmd_audit,
        "policy-check": cmd_policy_check,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
