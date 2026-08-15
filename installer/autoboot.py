#!/usr/bin/env python3
"""Hive OS Termux autoboot manager.

Commands:
  hive autoboot enable   -- install managed .bashrc block
  hive autoboot disable  -- disable autoboot (keep block, set flag)
  hive autoboot status   -- show autoboot state
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


BASHRC_MARKERS = ("# >>> HIVE OS AUTOBOOT >>>", "# <<< HIVE OS AUTOBOOT <<<")
MANAGED_BLOCK_TEMPLATE = """# >>> HIVE OS AUTOBOOT >>>
# Hive OS managed startup block. Safe to edit outside markers.
# To disable autoboot: hive autoboot disable
# To remove this block: hive autoboot disable --remove
# To skip once: export HIVE_NO_AUTOBOOT=1 before starting shell
case $- in
    *i*) ;;
    *) return ;;
esac
if [ -n "${HIVE_NO_AUTOBOOT:-}" ]; then
    return
fi
if [ -f "$HOME/.config/hive/no-autoboot" ]; then
    return
fi
if [ -n "${HIVE_BOOT_ACTIVE:-}" ]; then
    return
fi
export HIVE_BOOT_ACTIVE=1
HIVE_INSTALL_DIR="${HIVE_INSTALL_DIR:-$HOME/Hive-Ops}"
if [ -x "$HIVE_INSTALL_DIR/bin/hive" ]; then
    "$HIVE_INSTALL_DIR/bin/hive" boot
fi
unset HIVE_BOOT_ACTIVE
# <<< HIVE OS AUTOBOOT <<<
""".strip() + "\n"


def _bashrc_path() -> Path:
    home = Path.home()
    # On Termux, bashrc may not exist yet.
    return home / ".bashrc"
def _no_autoboot_file() -> Path:
    return Path.home() / ".config" / "hive" / "no-autoboot"



def _backup_bashrc(bashrc: Path) -> Path | None:
    if not bashrc.exists():
        return None
    backup = bashrc.with_suffix(".bashrc.hive-backup")
    # Only backup once.
    if not backup.exists():
        backup.write_text(bashrc.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def _block_present(bashrc: Path) -> bool:
    if not bashrc.exists():
        return False
    text = bashrc.read_text(encoding="utf-8")
    return BASHRC_MARKERS[0] in text and BASHRC_MARKERS[1] in text


def _remove_block(bashrc: Path) -> bool:
    if not bashrc.exists():
        return False
    text = bashrc.read_text(encoding="utf-8")
    start = text.find(BASHRC_MARKERS[0])
    end = text.find(BASHRC_MARKERS[1])
    if start == -1 or end == -1:
        return False
    end += len(BASHRC_MARKERS[1])
    new_text = text[:start] + text[end:]
    # Strip at most one trailing newline from the cut site.
    if new_text.endswith("\n\n"):
        new_text = new_text[:-1]
    bashrc.write_text(new_text, encoding="utf-8")
    return True


def _install_block(bashrc: Path, install_dir: Path) -> None:
    _backup_bashrc(bashrc)
    # Remove any stale block first to keep idempotency.
    _remove_block(bashrc)
    # Clear persistent disable flag if present.
    no_autoboot = _no_autoboot_file()
    if no_autoboot.exists():
        no_autoboot.unlink()
    existing = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
    install_dir_escaped = str(install_dir).replace('"', '\"')
    block = MANAGED_BLOCK_TEMPLATE.replace(
        ':-$HOME/Hive-Ops}',
        f':-{install_dir_escaped}}}',
    )
    # Ensure exactly one newline between existing content and block.
    if existing and not existing.endswith("\n"):
        existing += "\n"
    bashrc.write_text(existing + block, encoding="utf-8")


def _disable_block(bashrc: Path, remove: bool = False) -> bool:
    if remove:
        return _remove_block(bashrc)
    if not bashrc.exists():
        return False
    text = bashrc.read_text(encoding="utf-8")
    if BASHRC_MARKERS[0] not in text:
        return False
    # Insert HIVE_NO_AUTOBOOT=1 at top of the managed block.
    new_text = text.replace(
        BASHRC_MARKERS[0],
        f"{BASHRC_MARKERS[0]}\n# Autoboot disabled by hive autoboot disable\nexport HIVE_NO_AUTOBOOT=1",
        1,
    )
    if new_text == text:
        return False
    bashrc.write_text(new_text, encoding="utf-8")
    # Also create persistent disable file for robustness.
    no_autoboot = _no_autoboot_file()
    no_autoboot.parent.mkdir(parents=True, exist_ok=True)
    no_autoboot.write_text("disabled", encoding="utf-8")
    return True


def _is_enabled(bashrc: Path) -> bool | None:
    if _no_autoboot_file().exists():
        return False
    if not _block_present(bashrc):
        return None
    text = bashrc.read_text(encoding="utf-8")
    block_start = text.find(BASHRC_MARKERS[0])
    block_end = text.find(BASHRC_MARKERS[1])
    if block_start == -1 or block_end == -1:
        return None
    block = text[block_start:block_end]
    return "HIVE_NO_AUTOBOOT=1" not in block


def _status_line(bashrc: Path) -> str:
    if not _block_present(bashrc):
        return "disabled (no managed block)"
    enabled = _is_enabled(bashrc)
    if enabled is True:
        return "enabled"
    if enabled is False:
        return "disabled (HIVE_NO_AUTOBOOT set in block)"
    return "unknown"


def cmd_enable(args: argparse.Namespace) -> int:
    bashrc = _bashrc_path()
    install_dir = Path(args.install_dir) if args.install_dir else Path.home() / "Hive-Ops"
    _install_block(bashrc, install_dir)
    print(f"Hive autoboot enabled in {bashrc}")
    print(f"Install directory: {install_dir}")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    bashrc = _bashrc_path()
    if not _block_present(bashrc):
        print("Hive autoboot block not present.")
        return 0
    if _disable_block(bashrc, remove=args.remove):
        action = "removed" if args.remove else "disabled"
        print(f"Hive autoboot {action} in {bashrc}")
        return 0
    print("Hive autoboot was already disabled or block not found.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    bashrc = _bashrc_path()
    print(f"bashrc: {bashrc}")
    print(f"state:  {_status_line(bashrc)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive autoboot")
    subparsers = parser.add_subparsers(dest="action", required=True)

    enable = subparsers.add_parser("enable", help="enable Hive autoboot in .bashrc")
    enable.add_argument("--install-dir", help="path to Hive-Ops installation")
    enable.set_defaults(func=cmd_enable)

    disable = subparsers.add_parser("disable", help="disable Hive autoboot")
    disable.add_argument("--remove", action="store_true", help="remove the managed block entirely")
    disable.set_defaults(func=cmd_disable)

    status = subparsers.add_parser("status", help="show autoboot state")
    status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
