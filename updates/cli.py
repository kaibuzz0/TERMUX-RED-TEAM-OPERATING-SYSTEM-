"""CLI surface for `hive update *` commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from updates import TrustStore, BundleVerifier
from updates.errors import UpdateError
from updates.recovery_cli import _print_json


def cmd_status(args: argparse.Namespace) -> int:
    print("Update status placeholder: no update in progress.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    print("No network update checking configured; use offline bundles.")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    from updates.bundle import extract_bundle
    from updates.metadata import parse_metadata
    from updates.manifest import load_manifest
    bundle = Path(args.bundle)
    work = args.work_dir or Path("/tmp/hive-update-inspect")
    try:
        extract_bundle(bundle, work)
        metadata = parse_metadata((work / "metadata.json").read_text(encoding="utf-8"))
        manifest = load_manifest(work / "manifest.json")
        _print_json({
            "metadata": metadata,
            "manifest_artifact_count": len(manifest),
            "bundle_root": str(work),
        })
        return 0
    except Exception as e:
        print(f"Inspect failed: {e}", file=sys.stderr)
        return 2


def cmd_plan(args: argparse.Namespace) -> int:
    from updates.planner import plan_update
    bundle_root = Path(args.bundle)
    active_root = Path(args.active_root) if args.active_root else None
    try:
        plan = plan_update(bundle_root, active_root)
        _print_json(plan)
        return 0
    except Exception as e:
        print(f"Plan failed: {e}", file=sys.stderr)
        return 2


def cmd_verify(args: argparse.Namespace) -> int:
    trust = TrustStore.from_pem_file(Path(args.trust_store))
    verifier = BundleVerifier(trust, args.platform, args.architecture, args.current_sequence)
    for seq in args.revoked_sequence or []:
        verifier.add_revoked_sequence(seq)
    work = Path(args.work_dir or "/tmp/hive-update-verify")
    try:
        result = verifier.verify(Path(args.bundle), work, allow_emergency=args.emergency)
        _print_json({
            "verified": True,
            "release_id": result["metadata"]["release"]["release_id"],
            "version": result["metadata"]["release"]["version"],
            "trust_level": result["trust_level"],
            "manifest_artifact_count": len(result["manifest"]),
        })
        return 0
    except Exception as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        return 2


def cmd_stage(args: argparse.Namespace) -> int:
    from updates.updater import Updater
    updater = Updater(Path(args.release_root))
    try:
        staged = updater.stage(Path(args.bundle))
        print(f"Staged to {staged}")
        return 0
    except Exception as e:
        print(f"Stage failed: {e}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive update")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show update status")
    sub.add_parser("check", help="Check for updates (offline by default)")

    inspect_p = sub.add_parser("inspect", help="Inspect a bundle")
    inspect_p.add_argument("bundle")
    inspect_p.add_argument("--work-dir")

    plan_p = sub.add_parser("plan", help="Plan update against active release")
    plan_p.add_argument("bundle")
    plan_p.add_argument("--active-root")

    verify_p = sub.add_parser("verify", help="Verify a bundle")
    verify_p.add_argument("bundle")
    verify_p.add_argument("--trust-store", required=True)
    verify_p.add_argument("--platform", default="termux")
    verify_p.add_argument("--architecture", default="aarch64")
    verify_p.add_argument("--current-sequence", type=int, default=0)
    verify_p.add_argument("--revoked-sequence", type=int, action="append")
    verify_p.add_argument("--work-dir")
    verify_p.add_argument("--emergency", action="store_true")

    stage_p = sub.add_parser("stage", help="Stage a verified bundle")
    stage_p.add_argument("bundle")
    stage_p.add_argument("--release-root", required=True)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "status": cmd_status,
        "check": cmd_check,
        "inspect": cmd_inspect,
        "plan": cmd_plan,
        "verify": cmd_verify,
        "stage": cmd_stage,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
