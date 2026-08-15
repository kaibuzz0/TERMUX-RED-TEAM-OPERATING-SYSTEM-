"""CLI surface for `hive notes` and `hive speak` and `hive shell`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from config_engine import get_config
from hive_operator import (
    clear_notes,
    disable,
    enable,
    notes_info,
    read_notes,
    save_notes,
    speak,
    status,
)


def _config_root() -> Path:
    return Path(get_config("runtime").get("config_root", str(Path.home() / ".config" / "hive")))


def _repo_root() -> Path:
    from lib.hive_path import resolve_repository_root_from_file
    return resolve_repository_root_from_file(__file__)


def cmd_speak(args: argparse.Namespace) -> int:
    print(speak(_repo_root() if args.repo else None))
    return 0


def cmd_notes_show(args: argparse.Namespace) -> int:
    notes, migrated = read_notes(_config_root())
    print(notes)
    if migrated:
        print("(migrated from ~/.hive_ops.txt)", file=sys.stderr)
    return 0


def cmd_notes_info(args: argparse.Namespace) -> int:
    import json
    print(json.dumps(notes_info(_config_root()), indent=2))
    return 0


def cmd_notes_edit(args: argparse.Namespace) -> int:
    import shutil
    import subprocess
    config_root = _config_root()
    notes, _ = read_notes(config_root)
    path = save_notes(config_root, notes)
    editor = os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vim") or shutil.which("vi")
    if editor:
        subprocess.run([editor, str(path)])
        return 0
    print("No editor found.", file=sys.stderr)
    return 1


def cmd_notes_clear(args: argparse.Namespace) -> int:
    if clear_notes(_config_root()):
        print("Notes cleared.")
    else:
        print("No notes to clear.")
    return 0


def cmd_shell_status(args: argparse.Namespace) -> int:
    from pathlib import Path
    import json
    shell = args.shell or ("zsh" if Path.home().joinpath(".zshrc").exists() else "bash")
    rc = Path.home() / (".zshrc" if shell == "zsh" else ".bashrc")
    print(json.dumps(status(rc), indent=2))
    return 0


def cmd_shell_enable(args: argparse.Namespace) -> int:
    from pathlib import Path
    import json
    shell = args.shell or ("zsh" if Path.home().joinpath(".zshrc").exists() else "bash")
    rc = Path.home() / (".zshrc" if shell == "zsh" else ".bashrc")
    print(json.dumps(enable(rc), indent=2))
    return 0


def cmd_shell_disable(args: argparse.Namespace) -> int:
    from pathlib import Path
    import json
    shell = args.shell or ("zsh" if Path.home().joinpath(".zshrc").exists() else "bash")
    rc = Path.home() / (".zshrc" if shell == "zsh" else ".bashrc")
    print(json.dumps(disable(rc), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive operator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_speak = sub.add_parser("speak", help="Hive identity signal")
    p_speak.add_argument("--repo", action="store_true", help="Use repo escape.txt if present")
    p_speak.set_defaults(func=cmd_speak)

    notes = sub.add_parser("notes", help="Operator notes")
    notes_sub = notes.add_subparsers(dest="notes_cmd", required=True)
    notes_sub.add_parser("show", help="Show notes").set_defaults(func=cmd_notes_show)
    notes_sub.add_parser("info", help="Show notes info").set_defaults(func=cmd_notes_info)
    notes_sub.add_parser("edit", help="Edit notes").set_defaults(func=cmd_notes_edit)
    notes_sub.add_parser("clear", help="Clear notes").set_defaults(func=cmd_notes_clear)

    shell = sub.add_parser("shell", help="Shell integration")
    shell_sub = shell.add_subparsers(dest="shell_cmd", required=True)
    for name in ("status", "enable", "disable"):
        p = shell_sub.add_parser(name, help=f"{name.capitalize()} Hive shell integration")
        p.add_argument("--shell", choices=["bash", "zsh"])
        p.set_defaults(func=globals()[f"cmd_shell_{name}"])

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    import os
    raise SystemExit(main(sys.argv[1:]))
