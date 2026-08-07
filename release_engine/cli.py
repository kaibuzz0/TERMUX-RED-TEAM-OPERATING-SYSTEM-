"""Release engine CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from release_engine.builder import build_release
from release_engine.channels import ReleaseChannel, parse_channel
from release_engine.errors import ReleaseEngineError
from release_engine.registry import ReleaseRegistry
from release_engine.sbom import generate_sbom
from release_engine.signing import load_private_key, sign_release_metadata
from release_engine.verifier import inspect_release, verify_release_bundle
from release_engine.version import parse_release_version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hive release")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="show release engine version")

    p_build = sub.add_parser("build", help="build a deterministic release")
    p_build.add_argument("--source", required=True, type=Path)
    p_build.add_argument("--output", required=True, type=Path)
    p_build.add_argument("--version", required=True)
    p_build.add_argument("--sequence", type=int, default=1)
    p_build.add_argument("--build-id", default="local")
    p_build.add_argument("--revision", default="unknown")
    p_build.add_argument("--platforms", nargs="+", default=["linux"])
    p_build.add_argument("--architectures", nargs="+", default=["aarch64"])
    p_build.add_argument("--channel", default="stable")

    sub.add_parser("manifest", help="generate manifest from source")

    p_inspect = sub.add_parser("inspect", help="inspect a release bundle")
    p_inspect.add_argument("bundle", type=Path)
    p_inspect.add_argument("--work-dir", type=Path, default=None)

    p_sign = sub.add_parser("sign", help="sign release metadata")
    p_sign.add_argument("--metadata", required=True, type=Path)
    p_sign.add_argument("--private-key", required=True, type=Path)
    p_sign.add_argument("--key-id", required=True)
    p_sign.add_argument("--output", required=True, type=Path)

    p_verify = sub.add_parser("verify", help="verify a release bundle")
    p_verify.add_argument("bundle", type=Path)
    p_verify.add_argument("--trust-store", required=True, type=Path)
    p_verify.add_argument("--work-dir", type=Path, default=None)
    p_verify.add_argument("--current-sequence", type=int, default=0)

    p_list = sub.add_parser("list", help="list registered releases")
    p_list.add_argument("--registry", required=True, type=Path)

    p_status = sub.add_parser("status", help="show active release")
    p_status.add_argument("--registry", required=True, type=Path)

    p_channels = sub.add_parser("channels", help="show valid channels")

    p_deps = sub.add_parser("dependencies", help="inspect dependency metadata")
    p_deps.add_argument("metadata", type=Path)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        if args.command == "version":
            print(json.dumps({"release_engine_version": "1.0"}))
            return 0

        if args.command == "build":
            result = build_release(
                source_dir=args.source,
                output_dir=args.output,
                version=args.version,
                release_sequence=args.sequence,
                build_id=args.build_id,
                source_revision=args.revision,
                platforms=args.platforms,
                architectures=args.architectures,
                channel=args.channel,
            )
            print(json.dumps(result, indent=2, default=str))
            return 0

        if args.command == "inspect":
            work_dir = args.work_dir or args.bundle.parent / ".inspect"
            result = inspect_release(args.bundle, work_dir)
            print(json.dumps(result, indent=2, default=str))
            return 0

        if args.command == "sign":
            metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
            key = load_private_key(args.private_key)
            signed = sign_release_metadata(metadata, key, args.key_id, metadata.get("manifest_digest", ""))
            args.output.write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
            return 0

        if args.command == "verify":
            from updates.trust import TrustStore

            trust = TrustStore.from_pem_file(args.trust_store)
            work_dir = args.work_dir or args.bundle.parent / ".verify"
            result = verify_release_bundle(args.bundle, work_dir, trust, args.current_sequence)
            print(json.dumps({"verified": True, "release_id": result["metadata"].get("release", {}).get("release_id")}))
            return 0

        if args.command == "list":
            reg = ReleaseRegistry(args.registry)
            print(json.dumps([r.__dict__ for r in reg.list_releases()], indent=2))
            return 0

        if args.command == "status":
            reg = ReleaseRegistry(args.registry)
            active = reg.get_active()
            print(json.dumps(active.__dict__ if active else {}, indent=2))
            return 0

        if args.command == "channels":
            print(json.dumps([c.value for c in ReleaseChannel], indent=2))
            return 0

        if args.command == "dependencies":
            meta = json.loads(args.metadata.read_text(encoding="utf-8"))
            print(json.dumps(meta.get("dependencies", []), indent=2))
            return 0

        return 1
    except ReleaseEngineError as exc:
        print(f"[release] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[release] unexpected error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
