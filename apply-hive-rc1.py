#!/usr/bin/env python3
"""Apply a Hive OS parity-test bundle on a legacy 1.0.0 phone.

This script ships inside the release bundle and uses the bundle's own
updates/ and installer/ modules so it works on a phone that predates the
`hive update verify/plan/apply` surface.

Usage:
  python3 apply-hive-rc1.py --bundle hive-os-1.1.0-rc.1-20260815-parity.tar.gz --approve
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a Hive OS parity-test bundle")
    parser.add_argument("--bundle", required=True, help="path to signed tar.gz bundle")
    parser.add_argument("--trust-store", default="updates/trust_store/hive-parity-test.pem")
    parser.add_argument("--platform", default="termux")
    parser.add_argument("--architecture", default="aarch64")
    parser.add_argument("--current-sequence", type=int, default=20)
    parser.add_argument("--data-root", default=str(Path.home() / "Hive-Ops" / "data"))
    parser.add_argument("--state-root", default=str(Path.home() / "Hive-Ops" / "state"))
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))

    from updates.bundle import extract_bundle
    from updates.trust import TrustStore
    from updates.verifier import BundleVerifier
    from updates.metadata import parse_metadata
    from installer.activate import ActiveState
    from installer.plan import generate_plan
    from installer.schema import TargetPolicy

    bundle_path = Path(args.bundle).resolve()
    work = script_dir / ".apply-work"
    if work.exists():
        shutil.rmtree(work)

    print("[1/5] Extracting bundle...")
    extract_bundle(bundle_path, work)

    print("[2/5] Verifying signature and manifest...")
    trust = TrustStore.from_pem_file(script_dir / args.trust_store)
    verifier = BundleVerifier(trust, args.platform, args.architecture, args.current_sequence)
    result = verifier.verify(bundle_path, work / "verify", allow_emergency=False)
    metadata = result["metadata"]
    release_id = metadata["release"]["release_id"]
    print(f"  verified {release_id}")

    print("[3/5] Preparing installer layout...")
    staging_root = work / "staged"
    runtime_dir = staging_root / "data" / "runtime"
    runtime_dir.mkdir(parents=True)
    manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    for item in work.rglob("*"):
        if item.is_file() and item.name not in {"manifest.json", "metadata.json"}:
            rel = item.relative_to(work)
            dst = runtime_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)
    (staging_root / "state").mkdir(parents=True, exist_ok=True)
    (staging_root / "state" / "manifest.json").write_text(
        json.dumps({"manifest": manifest}, indent=2), encoding="utf-8"
    )
    shutil.copy2(work / "metadata.json", staging_root / "metadata.json")

    data_root = Path(args.data_root)
    state_root = Path(args.state_root)
    data_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)

    plan = generate_plan(script_dir, transaction_id=release_id)
    plan.target = TargetPolicy(
        root=data_root,
        config_root=state_root / "config",
        state_root=state_root,
        data_root=data_root,
        cache_root=state_root / "cache",
        log_root=state_root / "logs",
        staging_root=state_root / "staging",
    )

    print("[4/5] Promoting to ready...")
    state = ActiveState(data_root=data_root, state_root=state_root, transaction_id=release_id)
    state.promote_to_ready(staging_root, plan)

    if not args.approve:
        print("[5/5] Ready. Re-run with --approve to activate.")
        return 0

    print("[5/5] Activating...")
    state.activate(release_id, approve=True)
    print(f"Activated {release_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
