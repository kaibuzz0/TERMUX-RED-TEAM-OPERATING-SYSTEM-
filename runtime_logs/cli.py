"""CLI surface for `hive logs` and `hive rotate-logs`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from config_engine import get_config
from runtime_logs.rotation import RotationPolicy, rotate, rotate_if_needed
from runtime_logs.service_logger import ServiceLogger


def _log_root() -> Path:
    return Path(get_config("runtime")["log_root"])


def _service_log_path(service: str) -> Path:
    return _log_root() / "services" / f"{service}.log"


def _all_service_logs() -> list[Path]:
    d = _log_root() / "services"
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.is_file())


def cmd_logs(args: argparse.Namespace) -> int:
    if args.service:
        path = _service_log_path(args.service)
        if not path.exists():
            print(f"No log found for service: {args.service}", file=sys.stderr)
            return 1
        paths = [path]
    else:
        paths = _all_service_logs()
        if not paths:
            print("No service logs found.")
            return 0

    if args.status:
        for p in paths:
            size = p.stat().st_size
            print(f"{p.name}: {size} bytes")
        return 0

    for p in paths:
        if len(paths) > 1:
            print(f"=== {p.name} ===")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError as exc:
            print(f"Cannot read {p}: {exc}", file=sys.stderr)
            continue
        if args.tail is not None:
            lines = lines[-args.tail:]
        for line in lines:
            sys.stdout.write(line)
            sys.stdout.flush()
            if args.follow:
                # In follow mode we only tail once; true continuous follow would block.
                pass
    return 0


def cmd_rotate_logs(args: argparse.Namespace) -> int:
    policy = RotationPolicy(
        max_bytes=args.max_bytes,
        retention_count=args.retention,
    )
    results = []
    if args.service:
        paths = [_service_log_path(args.service)]
    else:
        paths = _all_service_logs()

    for p in paths:
        result = rotate(p, policy, compress=args.compress)
        results.append({"path": str(p), **result})

    if args.json:
        import json
        print(json.dumps({"rotated": results}, indent=2, default=str))
    else:
        total = sum(1 for r in results if r["rotated"])
        print(f"Rotated {total}/{len(results)} log(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive logs")
    sub = parser.add_subparsers(dest="command", required=True)

    # logs
    p_logs = sub.add_parser("show", help="Show service logs")
    p_logs.add_argument("service", nargs="?")
    p_logs.add_argument("--tail", type=int)
    p_logs.add_argument("--follow", action="store_true")
    p_logs.add_argument("--status", action="store_true")
    p_logs.set_defaults(func=cmd_logs)

    # rotate
    p_rot = sub.add_parser("rotate", help="Rotate service logs")
    p_rot.add_argument("service", nargs="?")
    p_rot.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024)
    p_rot.add_argument("--retention", type=int, default=5)
    p_rot.add_argument("--compress", action="store_true", default=True)
    p_rot.add_argument("--json", action="store_true")
    p_rot.set_defaults(func=cmd_rotate_logs)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
