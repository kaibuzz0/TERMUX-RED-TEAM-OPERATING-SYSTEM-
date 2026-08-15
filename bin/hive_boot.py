#!/usr/bin/env python3
"""Hive OS interactive boot menu (Milestone 18).

Lightweight home interface that delegates to existing `hive` subcommands.
Uses only stdlib so it runs under requirements-runtime.txt.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _resolve_hive_root() -> Path:
    # Prefer HIVE_REPO_ROOT env var, then canonical repo at ~/Hive-Ops, then cwd.
    env_root = os.environ.get("HIVE_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    default = Path.home() / "Hive-Ops"
    if (default / "bin" / "hive").exists():
        return default
    # Fallback: derive from this script location when run from source.
    return Path(__file__).resolve().parent.parent


def _hive_cmd(repo_root: Path) -> list[str]:
    return [sys.executable, str(repo_root / "bin" / "hive")]


def _run(repo_root: Path, *args: str) -> int:
    cmd = _hive_cmd(repo_root) + list(args)
    env = os.environ.copy()
    env["HIVE_REPO_ROOT"] = str(repo_root)
    # Ensure PYTHONPATH includes repo root for module-based delegations.
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        return subprocess.run(cmd, env=env).returncode
    except FileNotFoundError:
        print(f"hive: command not found: {cmd[0]}", file=sys.stderr)
        return 127


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")


def _print_menu() -> None:
    print("=" * 56)
    print("              Hive OS Interactive Home")
    print("=" * 56)
    print("  [1] Status overview          (hive ops overview)")
    print("  [2] Operations Center        (hive ops --json)")
    print("  [3] Broker capabilities      (hive broker capabilities)")
    print("  [4] Service status           (hive service list)")
    print("  [5] Policy status            (hive policy status)")
    print("  [6] Vault status             (hive vault status)")
    print("  [7] Configuration            (hive config validate)")
    print("  [8] Help                     (hive --help)")
    print("  [0] Exit to Termux shell")
    print("=" * 56)


def _read_choice() -> str:
    try:
        return input("Hive> ").strip()
    except (EOFError, KeyboardInterrupt):
        return "0"


def main(argv: list[str] | None = None) -> int:
    repo_root = _resolve_hive_root()
    if not (repo_root / "bin" / "hive").exists():
        print(f"hive-boot: cannot find Hive OS launcher at {repo_root / 'bin' / 'hive'}", file=sys.stderr)
        print("Run the Hive OS installer first:", file=sys.stderr)
        print('  bash -c "$(curl -fsSL .../install-termux-easy.sh)"', file=sys.stderr)
        return 1

    while True:
        _clear()
        _print_menu()
        choice = _read_choice()
        if choice == "0":
            print("Exiting Hive. Returning to Termux shell.")
            return 0
        dispatch = {
            "1": ("overview",),
            "2": ("ops", "--json"),
            "3": ("broker", "capabilities"),
            "4": ("service", "list"),
            "5": ("policy", "status"),
            "6": ("vault", "status"),
            "7": ("config", "validate"),
            "8": ("--help",),
        }.get(choice)
        if dispatch is None:
            print("Invalid choice. Press Enter to continue.")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                return 0
            continue
        print(f"\nRunning: hive {' '.join(dispatch)}\n")
        _run(repo_root, *dispatch)
        print("\nPress Enter to return to Hive menu.")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
