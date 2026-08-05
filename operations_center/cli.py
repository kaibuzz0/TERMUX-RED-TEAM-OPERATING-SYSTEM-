"""CLI surface for `hive ops *` commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from lib.hive_path import resolve_log_root, resolve_state_root
from operations_center.collectors import Collector
from operations_center.redaction import redact_value
from operations_center.render import render_json, render_text
from operations_center.schema import View


_VIEWS: dict[str, CallableFactory] = {
    "overview": lambda c: c.collect_overview(),
    "services": lambda c: c.collect_services(),
    "updates": lambda c: c.collect_updates(),
    "recovery": lambda c: c.collect_recovery(),
    "vault": lambda c: c.collect_vault(),
    "broker": lambda c: c.collect_broker(),
    "diagnostics": lambda c: c.collect_overview(),  # diagnostics are embedded in overview
    "events": lambda c: c.collect_overview(),
    "config": lambda c: c.collect_overview(),
}


class CallableFactory:
    """Placeholder to satisfy type hints."""

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, collector: Collector) -> dict[str, Any]:
        return self.fn(collector)


def _collect(view: str, timeout: int, verbose: bool) -> dict[str, Any]:
    state_root = resolve_state_root()
    log_root = resolve_log_root()
    collector = Collector(state_root, log_root, source_timeout=float(timeout))
    if view not in _VIEWS:
        return {"status": "failure", "errors": [f"Unknown view: {view}"]}
    return _VIEWS[view](collector)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive ops")
    parser.add_argument("view", nargs="?", default="overview", choices=list(_VIEWS))
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable color")
    parser.add_argument("--compact", action="store_true", help="Compact output")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--timeout", type=int, default=10, help="Source timeout seconds")
    parser.add_argument("--source-status", action="store_true", help="Include source status")
    args = parser.parse_args(argv)

    if args.view == "events":
        # Minimal events stub: derive from overview diagnostics and sources.
        data = _collect("overview", args.timeout, args.verbose)
        data["view"] = "events"
        data["data"] = {
            "events": data.get("diagnostics", []),
            "count": len(data.get("diagnostics", [])),
        }
    elif args.view == "config":
        data = {
            "schema_version": 1,
            "view": "config",
            "status": "success",
            "data": {
                "active_profile": "default",
                "schema_version": 1,
                "validation": "read-only-inspection",
                "write_behavior": "disabled",
            },
            "diagnostics": [],
            "errors": [],
        }
    elif args.view == "diagnostics":
        data = _collect("overview", args.timeout, args.verbose)
        data["view"] = "diagnostics"
        data["data"] = {"diagnostics": data.get("diagnostics", [])}
    else:
        data = _collect(args.view, args.timeout, args.verbose)

    if not args.source_status:
        data.pop("sources", None)

    safe = redact_value(data)

    if args.json:
        print(render_json(safe))
    else:
        print(render_text(safe, compact=args.compact, no_color=args.no_color))

    return 0 if data.get("status") in ("success", "partial") else 2


if __name__ == "__main__":
    sys.exit(main())
