"""CLI for Hive Policy Engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from policy_engine.audit import PolicyAudit
from policy_engine.engine import PolicyEngine
from policy_engine.requests import PolicyRequest
from policy_engine.validator import validate_policy_config


def _engine() -> PolicyEngine:
    return PolicyEngine.from_repo_root()


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_status(args: argparse.Namespace) -> int:
    engine = _engine()
    _print_json(engine.status())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from config_engine.config import get_config
    cfg = get_config("policy")
    warnings = validate_policy_config(cfg)
    result = {"valid": True, "warnings": warnings, "active_profile": cfg.get("active_profile", "observer")}
    if args.json:
        _print_json(result)
    else:
        print("policy configuration is valid" if not warnings else f"valid with {len(warnings)} warnings")
        for w in warnings:
            print(f"  warning: {w}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    engine = _engine()
    path = Path(args.request_file)
    if not path.is_file():
        print(f"Request file not found: {path}", file=sys.stderr)
        return 2
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 2
    decision = engine.evaluate(raw)
    result = decision.to_dict()
    result["execution_performed"] = False
    _print_json(result)
    return 0 if decision.decision.value in ("ALLOW", "NOT_APPLICABLE") else 1


def cmd_explain(args: argparse.Namespace) -> int:
    engine = _engine()
    result = engine.explain(args.capability, args.actor, args.resource)
    _print_json(result)
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    engine = _engine()
    _print_json({"profiles": engine.policy_set.list_profiles()})
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    engine = _engine()
    profile_name = args.profile or "observer"
    profile = engine.policy_set.get_profile(profile_name)
    rules = [
        {
            "rule_id": r.rule_id,
            "priority": r.priority,
            "effect": r.effect.value,
            "actors": sorted(r.actors) if r.actors else None,
            "capabilities": sorted(r.capabilities) if r.capabilities else None,
            "resources": sorted(r.resources) if r.resources else None,
            "reason_code": r.reason_code,
        }
        for r in sorted(profile.rules, key=lambda x: (-x.priority, x.rule_id))
    ]
    _print_json({"profile": profile_name, "rules": rules})
    return 0


def cmd_decisions(args: argparse.Namespace) -> int:
    engine = _engine()
    _print_json({"decision_count": len(engine.audit.records)})
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    engine = _engine()
    txn_id = args.transaction
    records = [r for r in engine.audit.records if r.get("transaction_id") == txn_id]
    _print_json({"transaction_id": txn_id, "records": records})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive policy")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--profile", help="Policy profile")
    parser.add_argument("--strict", action="store_true", help="Strict validation mode")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show policy engine status")
    sub.add_parser("validate", help="Validate policy configuration")

    eval_p = sub.add_parser("evaluate", help="Evaluate a policy request from a JSON file")
    eval_p.add_argument("request_file", help="Path to JSON request file")

    explain_p = sub.add_parser("explain", help="Explain decision for a capability")
    explain_p.add_argument("capability", help="Capability name")
    explain_p.add_argument("--actor", default="operator", help="Actor type")
    explain_p.add_argument("--resource", default="service", help="Resource type")

    sub.add_parser("profiles", help="List policy profiles")

    rules_p = sub.add_parser("rules", help="List rules for a profile")
    rules_p.add_argument("--profile", help="Profile name")

    sub.add_parser("decisions", help="Show buffered decisions")

    audit_p = sub.add_parser("audit", help="Lookup audit records by transaction ID")
    audit_p.add_argument("transaction", help="Transaction ID")

    args = parser.parse_args(argv)

    handlers = {
        "status": cmd_status,
        "validate": cmd_validate,
        "evaluate": cmd_evaluate,
        "explain": cmd_explain,
        "profiles": cmd_profiles,
        "rules": cmd_rules,
        "decisions": cmd_decisions,
        "audit": cmd_audit,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
