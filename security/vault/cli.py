"""CLI surface for `hive vault *` commands."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from security.vault import VaultSession, VaultError, VaultLockedError
from security.vault.migration import detect_legacy_credentials, build_migration_plan
from security.vault.redaction import redact


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_init(args: argparse.Namespace) -> int:
    session = VaultSession()
    if session.vault.exists() and not args.force:
        print("Vault already exists. Use --force to overwrite (not recommended).", file=sys.stderr)
        return 2
    password = getpass.getpass("Master password: ")
    confirm = getpass.getpass("Confirm master password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    try:
        session.init(password)
        print("Vault initialized.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def cmd_status(args: argparse.Namespace) -> int:
    session = VaultSession()
    status = session.status()
    if args.json:
        _print_json(status)
    else:
        print(f"Vault exists: {status['exists']}")
        print(f"Locked: {status['locked']}")
        print(f"Session state: {status['session_state']}")
        if status['secret_count'] is not None:
            print(f"Secrets: {status['secret_count']}")
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    session = VaultSession()
    password = getpass.getpass("Master password: ")
    try:
        session.unlock(password)
        print("Vault unlocked.")
        return 0
    except VaultError as e:
        print(f"Unlock failed: {e}", file=sys.stderr)
        return 2


def cmd_lock(args: argparse.Namespace) -> int:
    session = VaultSession()
    session.lock()
    print("Vault locked.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    session = VaultSession()
    try:
        records = session.vault.list(include_values=False)
        if args.json:
            _print_json({"secrets": records})
        else:
            for r in records:
                print(r["name"])
        return 0
    except VaultLockedError:
        print("Vault is locked. Run 'hive vault unlock' first.", file=sys.stderr)
        return 2


def cmd_set(args: argparse.Namespace) -> int:
    session = VaultSession()
    if session.locked():
        print("Vault is locked. Run 'hive vault unlock' first.", file=sys.stderr)
        return 2
    value = getpass.getpass("Secret value: ")
    try:
        session.vault.set(args.name, value, secret_type=args.type, scope=args.scope)
        session.vault.save(args.master_password or getpass.getpass("Master password to save: "))
        print(f"Secret '{args.name}' stored.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def cmd_get(args: argparse.Namespace) -> int:
    session = VaultSession()
    if session.locked():
        print("Vault is locked. Run 'hive vault unlock' first.", file=sys.stderr)
        return 2
    if not args.show:
        print("Secret values are not printed by default. Use --show with caution.", file=sys.stderr)
        return 2
    try:
        value = session.vault.get(args.name)
        print(value.decode("utf-8"))
        return 0
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def cmd_remove(args: argparse.Namespace) -> int:
    session = VaultSession()
    if session.locked():
        print("Vault is locked. Run 'hive vault unlock' first.", file=sys.stderr)
        return 2
    try:
        session.vault.remove(args.name)
        session.vault.save(args.master_password or getpass.getpass("Master password to save: "))
        print(f"Secret '{args.name}' removed.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def cmd_legacy_detect(args: argparse.Namespace) -> int:
    findings = detect_legacy_credentials()
    plan = build_migration_plan()
    if args.json:
        _print_json({"detection": redact(findings), "plan": redact(plan)})
    else:
        print(f"Legacy credentials detected: {findings['legacy_detected']}")
        print(f"Source: {findings.get('auth_file', 'n/a')}")
        if plan.get("can_migrate"):
            print("Migration plan available (non-executing).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--json", action="store_true", help="Output JSON")

    parser = argparse.ArgumentParser(prog="hive vault", description="Hive OS encrypted vault", parents=[parent])
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init", help="Initialize a new vault", parents=[parent])
    init_p.add_argument("--force", action="store_true", help="Overwrite existing vault")

    sub.add_parser("status", help="Show vault status", parents=[parent])
    sub.add_parser("unlock", help="Unlock the vault", parents=[parent])
    sub.add_parser("lock", help="Lock the vault", parents=[parent])
    sub.add_parser("list", help="List secret names", parents=[parent])

    set_p = sub.add_parser("set", help="Store a secret")
    set_p.add_argument("name")
    set_p.add_argument("--type", default="opaque")
    set_p.add_argument("--scope", default="OPERATOR_ONLY")
    set_p.add_argument("--master-password", help=argparse.SUPPRESS)

    get_p = sub.add_parser("get", help="Retrieve a secret")
    get_p.add_argument("name")
    get_p.add_argument("--show", action="store_true", help="Print secret value to terminal (insecure)")

    rm_p = sub.add_parser("remove", help="Remove a secret")
    rm_p.add_argument("name")
    rm_p.add_argument("--master-password", help=argparse.SUPPRESS)

    sub.add_parser("legacy-detect", help="Detect legacy credential files without mutation", parents=[parent])

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "unlock": cmd_unlock,
        "lock": cmd_lock,
        "list": cmd_list,
        "set": cmd_set,
        "get": cmd_get,
        "remove": cmd_remove,
        "legacy-detect": cmd_legacy_detect,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
