"""Main installer CLI surface.

Supported commands:
  python3 -m installer.install --check
  python3 -m installer.install --plan [--json]
  python3 -m installer.install --dry-run
  python3 -m installer.install --stage TARGET
  python3 -m installer.install --verify TARGET

No command automatically activates a production installation.
"""


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from installer.preflight import run_preflight, PreflightResult
from installer.plan import generate_plan, _load_canonical_metadata
from installer.schema import plan_to_dict
from installer.staging import StagingArea
from installer.verify import verify_staged_manifest


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_check(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    result = run_preflight(repo_root)
    if args.json:
        _print_json(result.to_dict())
    else:
        print("Preflight result:")
        print(f"  existing_installation: {result.existing_installation.value}")
        print(f"  classification:")
        for k, v in result.classification.items():
            print(f"    {k}: {v.value}")
        if result.warnings:
            print("  warnings:")
            for w in result.warnings:
                print(f"    - {w}")
        if result.errors:
            print("  errors:")
            for e in result.errors:
                print(f"    - {e}")
    return 0 if not result.errors else 2


def cmd_plan(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root, transaction_id=args.transaction_id)
    if args.json:
        _print_json(plan_to_dict(plan))
    else:
        print(f"Transaction: {plan.transaction_id}")
        print(f"Source: {plan.source.repository} @ {plan.source.commit[:8]}")
        print(f"Target root: {plan.target.root}")
        print(f"Operations: {len(plan.operations)}")
        for op in plan.operations:
            print(f"  {op.op_id} ({op.op_type})")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root, transaction_id=args.transaction_id)
    # Dry-run is identical to plan generation in this milestone: no mutation.
    pre = run_preflight(repo_root)
    if pre.errors:
        print("Preflight errors prevent dry-run:", file=sys.stderr)
        for e in pre.errors:
            print(f"  - {e}", file=sys.stderr)
        return 2
    if args.json:
        _print_json({
            "transaction_id": plan.transaction_id,
            "operations": [op.op_id for op in plan.operations],
            "target": str(plan.target.root),
            "existing_status": plan.existing_status.value,
            "would_mutate": False,
        })
    else:
        print("Dry-run complete. No files were changed.")
        print(f"Transaction: {plan.transaction_id}")
        print(f"Operations that would run: {len(plan.operations)}")
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    target = Path(args.target)
    if not target.exists():
        print(f"Target staging area does not exist: {target}", file=sys.stderr)
        return 2
    manifest_path = target / "manifest.json"
    result = verify_staged_manifest(target, manifest_path)
    if args.json:
        _print_json(result)
    else:
        print(f"Staging verification: {'valid' if result['valid'] else 'INVALID'}")
        print(f"Verified files: {result['verified_files']}")
        for err in result["errors"]:
            print(f"  ERROR: {err}")
    return 0 if result["valid"] else 2


def cmd_verify(args: argparse.Namespace) -> int:
    # Alias for --stage verification.
    return cmd_stage(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hive OS safe installer (Milestone 6)")
    parser.add_argument("--repo-root", type=Path, help="Repository root to install from")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--transaction-id", help="Explicit transaction identifier")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Run preflight checks")
    sub.add_parser("plan", help="Generate installation plan")
    sub.add_parser("dry-run", help="Validate plan without mutation")
    stage_p = sub.add_parser("stage", help="Verify a staged installation")
    stage_p.add_argument("target", type=Path, help="Path to staged area")
    verify_p = sub.add_parser("verify", help="Verify a staged installation")
    verify_p.add_argument("target", type=Path, help="Path to staged area")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "check": cmd_check,
        "plan": cmd_plan,
        "dry-run": cmd_dry_run,
        "stage": cmd_stage,
        "verify": cmd_verify,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
