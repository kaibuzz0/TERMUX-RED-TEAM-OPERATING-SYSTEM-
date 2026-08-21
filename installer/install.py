"""Main installer CLI surface.

Supported commands:
  python3 -m installer.install check
  python3 -m installer.install plan [--json]
  python3 -m installer.install dry-run
  python3 -m installer.install stage [TARGET]
  python3 -m installer.install verify [TARGET]
  python3 -m installer.install activate [TARGET] --approve
  python3 -m installer.install status
  python3 -m installer.install rollback --approve
  python3 -m installer.install legacy-detect

No command automatically activates a production installation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from installer.activate import ActiveState
from installer.legacy import build_migration_plan, detect_legacy_installation
from installer.plan import _load_canonical_metadata, generate_plan
from installer.preflight import run_preflight
from installer.schema import plan_to_dict, migration_plan_to_dict
from installer.staging import StagingArea
from installer.verify import verify_staged_manifest


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def _target_policy_from_plan(plan) -> dict:
    return {
        "root": plan.target.root,
        "state_root": plan.target.state_root,
        "data_root": plan.target.data_root,
    }


def cmd_check(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    result = run_preflight(repo_root)
    if args.json:
        _print_json(result.to_dict())
    else:
        print("Preflight result:")
        print(f"  existing_installation: {result.existing_installation.value}")
        print("  classification:")
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
    """Execute a staging plan. If no target given, generate a fresh plan and stage it."""
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root, transaction_id=args.transaction_id)
    area = StagingArea(plan)
    if args.target:
        target = Path(args.target)
        if target.exists():
            area.staging_root = target
    staged_root = area.stage_all()
    if args.json:
        _print_json({"staged_root": str(staged_root), "transaction_id": plan.transaction_id})
    else:
        print(f"Staged to: {staged_root}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    target = Path(args.target) if args.target else None
    if not target:
        print("--verify requires a TARGET", file=sys.stderr)
        return 2
    if not target.exists():
        print(f"Target staging area does not exist: {target}", file=sys.stderr)
        return 2
    manifest_path = target / "state" / "manifest.json"
    result = verify_staged_manifest(target, manifest_path)
    if args.json:
        _print_json(result)
    else:
        print(f"Staging verification: {'valid' if result['valid'] else 'INVALID'}")
        print(f"Verified files: {result['verified_files']}")
        for err in result["errors"]:
            print(f"  ERROR: {err}")
    return 0 if result["valid"] else 2


def _active_state_from_plan(plan) -> ActiveState:
    return ActiveState(
        data_root=plan.target.data_root,
        state_root=plan.target.state_root,
        transaction_id=plan.transaction_id,
    )


def cmd_activate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root, transaction_id=args.transaction_id)
    state = _active_state_from_plan(plan)

    target = Path(args.target) if args.target else plan.target.staging_root / plan.transaction_id
    if not target.exists():
        print(f"Staging area does not exist: {target}", file=sys.stderr)
        return 2

    release = state.promote_to_ready(target, plan)
    pointer = state.activate(release.release_id, approve=args.approve)
    if args.json:
        _print_json({
            "active_release_id": pointer.active_release_id,
            "active_runtime": pointer.active_runtime,
            "previous_release_id": pointer.previous_release_id,
        })
    else:
        print(f"Activated release: {pointer.active_release_id}")
        print(f"Runtime: {pointer.active_runtime}")
        if pointer.previous_release_id:
            print(f"Previous release preserved: {pointer.previous_release_id}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root)
    state = _active_state_from_plan(plan)
    status = state.status()
    if args.json:
        _print_json(status)
    else:
        print("Active installation status:")
        print(f"  data_root: {status['data_root']}")
        print(f"  locked: {status['locked']}")
        if status['lock_holder']:
            print(f"  lock_holder: {status['lock_holder']}")
        if status['active']:
            print(f"  active_release: {status['active']['active_release_id']}")
            print(f"  active_runtime: {status['active']['active_runtime']}")
            print(f"  previous_release: {status['active']['previous_release_id']}")
        else:
            print("  active_release: none")
        print(f"  releases: {len(status['releases'])}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    plan = generate_plan(repo_root)
    state = _active_state_from_plan(plan)
    pointer = state.rollback(approve=args.approve)
    if args.json:
        _print_json({
            "active_release_id": pointer.active_release_id,
            "active_runtime": pointer.active_runtime,
            "previous_release_id": pointer.previous_release_id,
        })
    else:
        print(f"Rolled back to release: {pointer.active_release_id}")
        print(f"Runtime: {pointer.active_runtime}")
        print(f"Failed/Previous release id: {pointer.previous_release_id}")
    return 0


def cmd_legacy_detect(args: argparse.Namespace) -> int:
    home = Path(args.home) if args.home else None
    legacy = build_migration_plan(home)
    if args.json:
        _print_json(migration_plan_to_dict(legacy))
    else:
        print(f"Legacy status: {legacy.legacy_status.value}")
        print(f"Reason: {legacy.classification_reason}")
        print(f"Safe items: {len(legacy.safe_items)}")
        print(f"Manual review items: {len(legacy.manual_review_items)}")
        print(f"Never-copy items: {len(legacy.never_copy_items)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--repo-root", type=Path, help="Repository root to install from")
    parent.add_argument("--json", action="store_true", help="Output JSON")
    parent.add_argument("--transaction-id", help="Explicit transaction identifier")
    parent.add_argument("--approve", action="store_true", help="Explicitly approve activation or rollback")
    parent.add_argument("--home", type=Path, help="Home directory for legacy detection")
    parent.add_argument("--force-stale-lock", action="store_true", help="Recover a stale installation lock")

    parser = argparse.ArgumentParser(description="Hive OS safe installer (Milestone 7)", parents=[parent])
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Run preflight checks", parents=[parent])
    sub.add_parser("plan", help="Generate installation plan", parents=[parent])
    sub.add_parser("dry-run", help="Validate plan without mutation", parents=[parent])
    stage_p = sub.add_parser("stage", help="Stage an installation", parents=[parent])
    stage_p.add_argument("target", type=Path, nargs="?", help="Optional staging path")
    verify_p = sub.add_parser("verify", help="Verify a staged installation", parents=[parent])
    verify_p.add_argument("target", type=Path, help="Path to staged area")
    activate_p = sub.add_parser("activate", help="Activate a staged installation (requires --approve)", parents=[parent])
    activate_p.add_argument("target", type=Path, nargs="?", help="Path to staged area")
    sub.add_parser("status", help="Show active installation status", parents=[parent])
    sub.add_parser("rollback", help="Roll back to previous release (requires --approve)", parents=[parent])
    sub.add_parser("legacy-detect", help="Detect legacy installations without mutation", parents=[parent])

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
        "activate": cmd_activate,
        "status": cmd_status,
        "rollback": cmd_rollback,
        "legacy-detect": cmd_legacy_detect,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
