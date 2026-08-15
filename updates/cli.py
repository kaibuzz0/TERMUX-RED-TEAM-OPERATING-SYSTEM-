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
    from updates.bundle import extract_bundle
    from updates.manifest import load_manifest
    import json, shutil
    work = Path(args.work_dir or "/tmp/hive-update-stage")
    if work.exists():
        shutil.rmtree(work)
    try:
        extract_bundle(Path(args.bundle), work)
        manifest = load_manifest(work / "manifest.json")
        release_id = json.loads((work / "metadata.json").read_text(encoding="utf-8"))["release"]["release_id"]
        target = Path(args.release_root) / release_id
        if target.exists():
            shutil.rmtree(target)
        runtime_dir = target / "data" / "runtime"
        runtime_dir.mkdir(parents=True)
        for entry in manifest:
            src = work / entry["path"]
            dst = runtime_dir / entry["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        staged_manifest = {"manifest": manifest}
        (target / "state" / "manifest.json").write_text(json.dumps(staged_manifest), encoding="utf-8")
        shutil.copy2(work / "metadata.json", target / "metadata.json")
        if args.json:
            _print_json({"staged_root": str(target), "release_id": release_id})
        else:
            print(f"Staged installer layout to {target}")
        return 0
    except Exception as e:
        print(f"Stage failed: {e}", file=sys.stderr)
        return 2




def cmd_apply(args: argparse.Namespace) -> int:
    """Verify, stage, and activate a signed offline bundle.

    Requires --trust-store, --release-root, and --approve.
    """
    if not args.approve:
        print("Activation requires --approve", file=sys.stderr)
        return 2

    from pathlib import Path
    from updates import TrustStore, BundleVerifier
    from updates.bundle import extract_bundle
    from updates.metadata import parse_metadata
    from installer.activate import ActiveState
    from installer.plan import generate_plan
    from installer.schema import plan_to_dict
    import json
    import shutil

    work = Path(args.work_dir or "/tmp/hive-update-apply")
    trust = TrustStore.from_pem_file(Path(args.trust_store))
    verifier = BundleVerifier(trust, args.platform, args.architecture, args.current_sequence)
    for seq in args.revoked_sequence or []:
        verifier.add_revoked_sequence(seq)

    try:
        verified = verifier.verify(Path(args.bundle), work)
    except Exception as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        return 2

    metadata = verified["metadata"]
    release_id = metadata["release"]["release_id"]

    # Use installer staging/activation against the active installation
    plan = generate_plan(work)
    state = ActiveState(
        data_root=plan.target.data_root,
        state_root=plan.target.state_root,
        transaction_id=plan.transaction_id,
    )
    release = state.promote_to_ready(work, plan)
    release.metadata = metadata
    pointer = state.activate(release_id, approve=True)

    if args.json:
        _print_json({
            "verified": True,
            "release_id": release_id,
            "version": metadata["release"]["version"],
            "active_runtime": pointer.active_runtime,
            "previous_release_id": pointer.previous_release_id,
        })
    else:
        print(f"Verified and activated: {release_id}")
        print(f"Version: {metadata['release']['version']}")
        print(f"Runtime: {pointer.active_runtime}")
        if pointer.previous_release_id:
            print(f"Previous release preserved: {pointer.previous_release_id}")
    return 0


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

    stage_p = sub.add_parser("stage", help="Stage a verified bundle into installer-compatible layout")
    stage_p.add_argument("bundle")
    stage_p.add_argument("--release-root", required=True)
    stage_p.add_argument("--work-dir")

    apply_p = sub.add_parser("apply", help="Verify, stage, and activate a bundle")
    apply_p.add_argument("bundle")
    apply_p.add_argument("--trust-store", required=True)
    apply_p.add_argument("--release-root", required=True)
    apply_p.add_argument("--platform", default="termux")
    apply_p.add_argument("--architecture", default="aarch64")
    apply_p.add_argument("--current-sequence", type=int, default=0)
    apply_p.add_argument("--revoked-sequence", type=int, action="append")
    apply_p.add_argument("--approve", action="store_true", help="Approve activation")
    apply_p.add_argument("--work-dir")

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
        "apply": cmd_apply,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
