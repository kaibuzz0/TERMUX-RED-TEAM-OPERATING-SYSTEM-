#!/usr/bin/env python3
"""Hive OS Interactive Home (Pass E).

Lightweight operator landing page.  All telemetry comes from authoritative
subsystems (network, services, diagnostics, operator notes).  No fake state.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from home.renderer import render
from home.view_model import build_home_state


def _resolve_hive_root() -> Path:
    env_root = os.environ.get("HIVE_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    default = Path.home() / "Hive-Ops"
    if (default / "bin" / "hive").exists():
        return default
    return Path(__file__).resolve().parent.parent


def _hive_cmd(repo_root: Path) -> list[str]:
    return [sys.executable, str(repo_root / "bin" / "hive")]


def _run(repo_root: Path, *args: str) -> int:
    cmd = _hive_cmd(repo_root) + list(args)
    env = os.environ.copy()
    env["HIVE_REPO_ROOT"] = str(repo_root)
    env["PYTHONPATH"] = str(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        return subprocess.run(cmd, env=env).returncode
    except FileNotFoundError:
        print(f"hive: command not found: {cmd[0]}", file=sys.stderr)
        return 127


def _clear() -> None:
    sys.stdout.write("\033[2J\033[H")


def _read(prompt: str = "Hive> ") -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "0"


def _pause() -> None:
    try:
        input("\nPress Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def _network_menu(repo_root: Path) -> None:
    while True:
        _clear()
        print("=" * 56)
        print("              Hive OS Network")
        print("=" * 56)
        print("  [1] Status   (hive net status)")
        print("  [2] DIRECT")
        print("  [3] ORBOT")
        print("  [4] TOR")
        print("  [5] HOLD")
        print("  [6] Test")
        print("  [7] New identity")
        print("  [8] Run command through profile")
        print("  [0] Back")
        print("=" * 56)
        choice = _read("Network> ")
        if choice == "0":
            return
        dispatch = {
            "1": ("net", "status"),
            "2": ("net", "direct"),
            "3": ("net", "orbot"),
            "4": ("net", "tor"),
            "5": ("net", "hold"),
            "6": ("net", "test"),
            "7": ("net", "newnym"),
            "8": ("net", "run", "--"),
        }.get(choice)
        if dispatch is None:
            print("Invalid choice.")
            _pause()
            continue
        if choice == "5":
            print("\nHOLD disables Hive proxy execution and network-dependent services.")
            print("It is NOT an Android device firewall.")
        _run(repo_root, *dispatch)
        _pause()


def _services_menu(repo_root: Path) -> None:
    while True:
        _clear()
        print("=" * 56)
        print("              Hive OS Services")
        print("=" * 56)
        print("  [1] Status        (hive services status)")
        print("  [2] List          (hive services list)")
        print("  [3] Ensure all    (hive start)")
        print("  [4] Stop all      (hive stop)")
        print("  [0] Back")
        print("=" * 56)
        choice = _read("Services> ")
        if choice == "0":
            return
        dispatch = {
            "1": ("services", "status"),
            "2": ("services", "list"),
            "3": ("start",),
            "4": ("stop",),
        }.get(choice)
        if dispatch is None:
            print("Invalid choice.")
            _pause()
            continue
        _run(repo_root, *dispatch)
        _pause()


def _security_menu(repo_root: Path) -> None:
    while True:
        _clear()
        print("=" * 56)
        print("              Hive OS Security / Audit")
        print("=" * 56)
        print("  [1] Health        (hive health)")
        print("  [2] Doctor        (hive doctor)")
        print("  [3] Audit         (hive audit)")
        print("  [4] Selftest      (hive selftest)")
        print("  [0] Back")
        print("=" * 56)
        print("  Audit is READ-ONLY. Selftest is an active test that restores state.")
        choice = _read("Security> ")
        if choice == "0":
            return
        if choice == "4":
            print("\nSelftest performs controlled temporary runtime tests and restores state.")
            confirm = _read("Run selftest? [y/N] ")
            if confirm.lower() != "y":
                continue
        dispatch = {
            "1": ("health",),
            "2": ("doctor",),
            "3": ("audit",),
            "4": ("selftest",),
        }.get(choice)
        if dispatch is None:
            print("Invalid choice.")
            _pause()
            continue
        _run(repo_root, *dispatch)
        _pause()


def _notes_menu(repo_root: Path) -> None:
    from config_engine import get_config
    from hive_operator.notes import clear_notes, read_notes, save_notes
    config_root = Path(get_config("runtime").get("config_root", str(Path.home() / ".config" / "hive")))
    while True:
        _clear()
        print("=" * 56)
        print("              Hive OS Operator Notes")
        print("=" * 56)
        notes, migrated = read_notes(config_root)
        if notes:
            print("\nCurrent notes:")
            for line in notes.splitlines()[:20]:
                print(f"  {line}")
        else:
            print("\nNo notes yet.")
        if migrated:
            print("  (migrated from ~/.hive_ops.txt)")
        print("\n  [1] Show all")
        print("  [2] Edit")
        print("  [3] Clear")
        print("  [0] Back")
        print("=" * 56)
        choice = _read("Notes> ")
        if choice == "0":
            return
        if choice == "1":
            _clear()
            print(notes)
            _pause()
        elif choice == "2":
            editor = os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vim") or shutil.which("vi")
            path = save_notes(config_root, notes)
            if editor:
                subprocess.run([editor, str(path)])
                notes, _ = read_notes(config_root)
                save_notes(config_root, notes)
            else:
                print("No editor found. Type new notes (Ctrl-D / Ctrl-Z to finish):")
                try:
                    new = sys.stdin.read()
                    save_notes(config_root, new)
                except (EOFError, KeyboardInterrupt):
                    pass
        elif choice == "3":
            if clear_notes(config_root):
                print("Notes cleared.")
            else:
                print("No notes to clear.")
            _pause()


def _main_menu(repo_root: Path) -> int:
    while True:
        _clear()
        try:
            state = build_home_state(repo_root)
            print(render(state), end="")
        except Exception as exc:
            print(f"\n[Hive Home telemetry error: {exc}]\n", file=sys.stderr)
        choice = _read("Hive> ")
        if choice == "0":
            print("\nExiting Hive. Returning to Termux shell.")
            return 0
        if choice.upper() == "R":
            continue
        if choice.upper() == "S":
            _run(repo_root, "speak")
            _pause()
            continue
        if choice.upper() == "U":
            _updates_menu(repo_root)
            continue
        if choice.upper() == "N":
            _notes_menu(repo_root)
            continue
        dispatch = {
            "1": ("ops", "overview"),
            "2": None,  # network submenu
            "3": None,  # services submenu
            "4": None,  # security submenu
            "5": ("vault", "status"),
            "6": ("plugins", "list"),
            "7": ("logs",),
            "8": ("doctor",),
            "9": ("termux", "repair"),
        }.get(choice)
        if choice == "2":
            _network_menu(repo_root)
        elif choice == "3":
            _services_menu(repo_root)
        elif choice == "4":
            _security_menu(repo_root)
        elif dispatch:
            _run(repo_root, *dispatch)
            _pause()
        else:
            print("Invalid choice.")
            _pause()


def main(argv: list[str] | None = None) -> int:
    repo_root = _resolve_hive_root()
    if not (repo_root / "bin" / "hive").exists():
        print(f"hive-boot: cannot find Hive OS launcher at {repo_root / 'bin' / 'hive'}", file=sys.stderr)
        print("Run the Hive OS installer first:", file=sys.stderr)
        return 1
    try:
        return _main_menu(repo_root)
    except KeyboardInterrupt:
        print("\n\nExiting Hive.")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
