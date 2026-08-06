"""CLI surface for `hive config *` commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config_engine import get_config
from config_engine.config import ConfigEngine
from config_engine.merger import strip_internal_keys


# Use a stable engine instance per CLI invocation to avoid repeated resolution.
_ENGINE: ConfigEngine | None = None


def _engine() -> ConfigEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ConfigEngine.from_repo_root()
    return _ENGINE


def _print_json(data: dict, indent: int = 2) -> None:
    print(json.dumps(data, indent=indent, default=str))


def cmd_show(args: argparse.Namespace) -> int:
    engine = _engine()
    if args.subsystem and args.sources:
        data = engine.show_with_sources(args.subsystem)
    else:
        config = engine.full_config()
        if args.subsystem:
            config = {args.subsystem: config.get(args.subsystem)}
        data = strip_internal_keys(config)
    if args.json:
        indent = engine.get_config("operations_center").get("json_indent", 2) if not args.subsystem else 2
        _print_json(data, indent=indent)
    else:
        if args.subsystem and args.sources:
            print(f"[{args.subsystem}]")
            for k, v in data.get("data", {}).items():
                src = data.get("sources", {}).get(k, "DEFAULT")
                print(f"  {k} = {v}  (source: {src})")
        else:
            for section, values in data.items():
                print(f"[{section}]")
                for k, v in values.items():
                    print(f"  {k} = {v}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    engine = _engine()
    try:
        engine.full_config()
        result = {"valid": True, "profile": engine.profile_name}
    except Exception as e:
        result = {"valid": False, "error": str(e)}
    if args.json:
        _print_json(result)
    else:
        print("valid" if result["valid"] else f"invalid: {result.get('error')}")
    return 0 if result["valid"] else 2


def cmd_preview(args: argparse.Namespace) -> int:
    engine = _engine()
    if args.file:
        from config_engine.loader import load_config_file
        candidate = load_config_file(Path(args.file))
    else:
        candidate = engine.full_config()
    output = engine.preview_commit(candidate)
    print(output)
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    engine = _engine()
    profiles = engine.profile_resolver.list_profiles()
    data = {"profiles": profiles, "active": engine.profile_name}
    if args.json:
        _print_json(data)
    else:
        print(f"Active profile: {data['active']}")
        for p in data["profiles"]:
            marker = " *" if p == data["active"] else ""
            print(f"  {p}{marker}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    engine = _engine()
    try:
        resolved = engine.profile_resolver.resolve(args.name)
    except Exception as e:
        print(f"profile resolution failed: {e}", file=sys.stderr)
        return 2
    if args.json:
        _print_json(resolved)
    else:
        print(f"Profile: {args.name}")
        for section, values in resolved.items():
            print(f"[{section}]")
            for k, v in values.items():
                print(f"  {k} = {v}")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    engine = _engine()
    info = engine.schema_info(args.subsystem)
    _print_json(info)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    engine = _engine()
    history = engine.history()
    if args.json:
        _print_json({"history": history})
    else:
        print(f"Transactions: {len(history)}")
        for record in history:
            print(f"  {record.get('transaction_id')} {record.get('profile')} {record.get('validation_result')} {record.get('timestamp')}")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    engine = _engine()
    try:
        result = engine.rollback(args.transaction)
    except Exception as e:
        print(f"rollback failed: {e}", file=sys.stderr)
        return 2
    if args.json:
        _print_json(result)
    else:
        print(f"Created rollback transaction: {result['transaction_id']}")
        print(f"Restored transaction: {result.get('restored_transaction')}")
    return 0



def cmd_explain(args: argparse.Namespace) -> int:
    engine = _engine()
    parts = args.target.split(".", 1)
    subsystem = parts[0]
    field = parts[1] if len(parts) > 1 else None
    info = engine.explain(subsystem, field)
    _print_json(info)
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive config")
    sub = parser.add_subparsers(dest="command")

    show_p = sub.add_parser("show", help="Show resolved configuration")
    show_p.add_argument("subsystem", nargs="?", help="Limit to one subsystem")
    show_p.add_argument("--json", action="store_true", help="Emit JSON")
    show_p.add_argument("--profile", help="Use a specific profile")
    show_p.add_argument("--sources", action="store_true", help="Show source provenance for each field")

    validate_p = sub.add_parser("validate", help="Validate current configuration")
    validate_p.add_argument("--json", action="store_true")
    validate_p.add_argument("--strict", action="store_true")

    preview_p = sub.add_parser("preview", help="Preview a configuration change without writing")
    preview_p.add_argument("--file", help="Path to candidate configuration file")
    preview_p.add_argument("--json", action="store_true")

    profiles_p = sub.add_parser("profiles", help="List available profiles")
    profiles_p.add_argument("--json", action="store_true")

    profile_p = sub.add_parser("profile", help="Show resolved profile contents")
    profile_p.add_argument("name")
    profile_p.add_argument("--json", action="store_true")

    schema_p = sub.add_parser("schema", help="Show schema for a subsystem")
    schema_p.add_argument("subsystem", nargs="?", default=None)
    schema_p.add_argument("--json", action="store_true")

    history_p = sub.add_parser("history", help="Show configuration history")
    history_p.add_argument("--json", action="store_true")

    explain_p = sub.add_parser("explain", help="Explain the source of a configuration field")
    explain_p.add_argument("target", help="subsystem or subsystem.field")
    explain_p.add_argument("--json", action="store_true")

    rollback_p = sub.add_parser("rollback", help="Rollback to a previous transaction")
    rollback_p.add_argument("transaction", help="Transaction ID to restore")
    rollback_p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "show": cmd_show,
        "validate": cmd_validate,
        "preview": cmd_preview,
        "profiles": cmd_profiles,
        "profile": cmd_profile,
        "schema": cmd_schema,
        "history": cmd_history,
        "rollback": cmd_rollback,
        "explain": cmd_explain,
    }

    # Handle profile override
    if getattr(args, "profile", None):
        global _ENGINE
        _ENGINE = ConfigEngine.from_repo_root(profile=args.profile)

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
