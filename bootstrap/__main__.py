"""Entry point for the Hive clean-install bootstrap package and zipapp."""

from __future__ import annotations

try:
    from bootstrap.install_release import main
except ImportError:  # pragma: no cover - exercised by standalone zipapp execution
    from install_release import main


if __name__ == "__main__":
    raise SystemExit(main())
