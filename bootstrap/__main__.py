"""Entry point for the Hive clean-install bootstrap package and zipapp."""

from __future__ import annotations

import sys

try:
    from bootstrap.install_release import main as install_main
    from bootstrap.verify_bundle import main as verify_main
except ImportError:  # pragma: no cover - exercised by standalone zipapp execution
    from install_release import main as install_main
    from verify_bundle import main as verify_main


def main(argv: list[str] | None = None) -> int:
    """Dispatch the standalone bootstrap command surface.

    New callers can use explicit ``install`` and ``verify`` subcommands. For
    compatibility with the first V2 zipapp prototype, installer flags supplied
    directly at archive root still route to the install command.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "verify":
        return verify_main(args[1:])
    if args and args[0] == "install":
        return install_main(args[1:])
    return install_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
