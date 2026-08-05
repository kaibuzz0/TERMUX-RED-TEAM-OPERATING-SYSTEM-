"""CLI surface for `hive recovery *` commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from updates.recovery import diagnose, repair_stale_locks


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_diagnose(args: argparse.Namespace) -> int:
    _print_json(diagnose(Path(args.release_root)))
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    _print_json(repair_stale_locks(Path(args.release_root), args.max_age))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive recovery")
    sub = parser.add_subparsers(dest="command")

    diag = sub.add_parser("diagnose", help="Non-mutating diagnosis")
    diag.add_argument("--release-root", required=True)

    repair = sub.add_parser("repair", help="Repair generated state")
    repair.add_argument("--release-root", required=True)
    repair.add_argument("--max-age", type=int, default=300)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    return {"diagnose": cmd_diagnose, "repair": cmd_repair}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
