"""Safe optional shell integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


HIVE_BASH_MARKER = "# Hive OS optional shell integration"
HIVE_ZSH_MARKER = "# Hive OS optional shell integration"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _backup_if_missing(path: Path) -> None:
    if path.exists() and not path.with_suffix(path.suffix + ".hive-bak").exists():
        path.with_suffix(path.suffix + ".hive-bak").write_bytes(path.read_bytes())


def _hive_aliases() -> str:
    return """
# Hive OS optional shell integration
alias hive-status='hive status'
alias hive-logs='hive logs'
alias hive-notes='hive notes show'
alias hive-doctor='hive doctor'
alias hive-audit='hive audit'
alias hive-health='hive health'
# End Hive OS optional shell integration
""".strip() + "\n"


def enable(rc_path: Path) -> dict[str, Any]:
    """Install managed Hive shell integration block."""
    _backup_if_missing(rc_path)
    text = rc_path.read_text(encoding="utf-8", errors="replace") if rc_path.exists() else ""
    if HIVE_BASH_MARKER in text:
        return {"installed": False, "reason": "already enabled"}
    text = text.rstrip() + "\n\n" + _hive_aliases() + "\n"
    rc_path.write_text(text, encoding="utf-8")
    return {"installed": True, "path": str(rc_path)}


def disable(rc_path: Path) -> dict[str, Any]:
    """Remove managed Hive shell integration block."""
    if not rc_path.exists():
        return {"removed": False, "reason": "file does not exist"}
    text = rc_path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"\n?# Hive OS optional shell integration.*?# End Hive OS optional shell integration\n", re.DOTALL)
    new_text = pattern.sub("", text)
    if new_text == text:
        return {"removed": False, "reason": "marker not found"}
    rc_path.write_text(new_text.strip() + "\n", encoding="utf-8")
    return {"removed": True, "path": str(rc_path)}


def status(rc_path: Path) -> dict[str, Any]:
    enabled = False
    if rc_path.exists():
        try:
            text = rc_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        enabled = HIVE_BASH_MARKER in text
    return {
        "enabled": enabled,
        "path": str(rc_path),
        "backup": str(rc_path.with_suffix(rc_path.suffix + ".hive-bak")) if rc_path.exists() else None,
    }
