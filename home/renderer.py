"""Hive Home renderer."""

from __future__ import annotations

import os
import sys
from typing import Any

from home.view_model import HiveHomeState


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() and os.environ.get("TERM") not in {"dumb", ""}


def _color(text: str, color: str) -> str:
    if not _supports_color():
        return text
    codes = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m",
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"


def _state_color(state: str) -> str:
    lower = state.lower()
    if any(word in lower for word in ("healthy", "online", "enforced", "available", "locked", "verified", "integrated", "idle")):
        return "green"
    if any(word in lower for word in ("degraded", "blocked", "warning")):
        return "yellow"
    if any(word in lower for word in ("failed", "error", "critical", "offline", "corrupt")):
        return "red"
    return "cyan"


def render(state: HiveHomeState, width: int = 58) -> str:
    lines: list[str] = []
    lines.append("=" * width)
    lines.append(_color(f"{'Hive OS':^{width}}", "bold"))
    lines.append(_color(f"{'Operator Environment':^{width}}", "bold"))
    lines.append("=" * width)

    rows = [
        ("Runtime", state.runtime),
        ("Supervisor", state.supervisor),
        ("Network", state.network_profile),
        ("Tor", state.tor_health),
        ("Services", state.services),
        ("Policy", state.policy),
        ("Broker", state.broker),
        ("Vault", state.vault),
        ("Trust", state.trust),
        ("Termux", state.termux),
    ]

    for label, value in rows:
        color = _state_color(value)
        lines.append(f"  {label:<12} {_color(value, color)}")

    if state.notes_preview:
        lines.append("-" * width)
        lines.append("Operator Notes")
        preview = state.notes_preview if len(state.notes_preview) <= 50 else state.notes_preview[:47] + "..."
        lines.append(f"  {preview}")

    if state.errors:
        lines.append("-" * width)
        lines.append(_color("Subsystem Errors", "red"))
        for err in state.errors:
            lines.append(f"  ! {err}")

    lines.append("=" * width)
    lines.append("  [1] Operations Center")
    lines.append("  [2] Network")
    lines.append("  [3] Services")
    lines.append("  [4] Security / Audit")
    lines.append("  [5] Vault")
    lines.append("  [6] Plugins")
    lines.append("  [7] Logs")
    lines.append("  [8] Diagnostics")
    lines.append("  [U] Updates")
    lines.append("  [9] Termux Integration / Repair")
    lines.append("  [N] Operator Notes")
    lines.append("  [S] Speak")
    lines.append("  [R] Refresh")
    lines.append("  [0] Exit to Termux")
    lines.append("=" * width)
    return "\n".join(lines) + "\n"
