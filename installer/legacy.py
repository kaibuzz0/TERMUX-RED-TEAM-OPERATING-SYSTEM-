"""Legacy installation detection and non-executable migration planning."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from installer.schema import LegacyStatus, MigrationPlan, MigrationRisk


class LegacyDetectionError(Exception):
    """Failure during legacy detection."""


# Patterns that indicate shell startup modifications.
_SHELL_STARTUP_FILES = {".bashrc", ".zshrc", ".profile", ".bash_profile"}

# Paths that must never be copied automatically.
_NEVER_COPY_NAMES = {
    "credentials",
    "auth.json",
    "secrets",
    ".env",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}


def _looks_like_base64(s: str) -> bool:
    if len(s) < 20:
        return False
    stripped = s.strip()
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9+/=]+", stripped))


def _file_contains_base64(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    for line in text.splitlines()[:20]:
        if _looks_like_base64(line):
            return True
    return False


def _classify_file(path: Path, legacy_root: Path) -> dict[str, Any]:
    rel = path.relative_to(legacy_root).as_posix()
    name = path.name.lower()
    reason = ""
    risk = MigrationRisk.UNKNOWN

    if name in _NEVER_COPY_NAMES or any(part.lower() in _NEVER_COPY_NAMES for part in path.parts):
        risk = MigrationRisk.NEVER_COPY
        reason = "credential/secret-like filename"
    elif path.suffix.lower() in {".sh", ".py"} and path.stat().st_size > 0:
        # Scripts are potentially executable; require manual review.
        risk = MigrationRisk.MANUAL_REVIEW
        reason = "executable script"
    elif _file_contains_base64(path):
        risk = MigrationRisk.NEVER_COPY
        reason = "appears to contain base64 credential material"
    elif name in _SHELL_STARTUP_FILES:
        risk = MigrationRisk.MANUAL_REVIEW
        reason = "shell startup file"
    elif path.is_dir() and "termux" in rel.lower():
        risk = MigrationRisk.MANUAL_REVIEW
        reason = "Termux-specific directory"
    elif path.is_file():
        risk = MigrationRisk.SAFE
        reason = "ordinary file"
    else:
        risk = MigrationRisk.UNKNOWN
        reason = "unclassified"

    return {
        "path": rel,
        "type": "directory" if path.is_dir() else "file",
        "size": path.stat().st_size if path.is_file() else 0,
        "risk": risk.value,
        "reason": reason,
    }


def detect_legacy_installation(
    home: Path | None = None,
    legacy_root_override: Path | None = None,
) -> dict[str, Any]:
    """Detect legacy installations and return structured findings without mutation."""
    home = home or Path(os.environ.get("HOME", "/tmp"))
    candidates = []

    if legacy_root_override:
        candidates.append(("override", legacy_root_override))
    else:
        candidates.extend([
            ("home_hive", home / "hive"),
            ("legacy_root", Path("/root/hive")),
        ])

    found = []
    for label, root in candidates:
        if root.exists() and root.is_dir():
            found.append((label, root))

    if not found:
        return {
            "legacy_status": LegacyStatus.NO_LEGACY_INSTALLATION.value,
            "legacy_root": None,
            "classification_reason": "No legacy installation paths found",
            "candidates": {label: str(root) for label, root in candidates},
        }

    # Prefer the first found; if multiple, report conflict.
    if len(found) > 1:
        primary_label, primary_root = found[0]
        return {
            "legacy_status": LegacyStatus.LEGACY_CONFLICT.value,
            "legacy_root": str(primary_root),
            "classification_reason": f"Multiple legacy installations found: {', '.join(f'{l}={r}' for l, r in found)}",
            "candidates": {label: str(root) for label, root in candidates},
        }

    primary_label, primary_root = found[0]

    # Inspect contents without modification.
    safe_items = []
    manual_review_items = []
    never_copy_items = []
    has_devai = False
    has_final = False
    has_bashrc = False
    has_boot = False
    has_base64_credential = False
    has_symlink = False

    for p in sorted(primary_root.rglob("*")):
        rel = p.relative_to(primary_root).as_posix()
        if any(part in {".git", "__pycache__"} for part in p.parts):
            continue
        entry = _classify_file(p, primary_root)
        if entry["risk"] == MigrationRisk.SAFE.value:
            safe_items.append(entry)
        elif entry["risk"] == MigrationRisk.MANUAL_REVIEW.value:
            manual_review_items.append(entry)
        elif entry["risk"] == MigrationRisk.NEVER_COPY.value:
            never_copy_items.append(entry)

        lower = rel.lower()
        if "devai" in lower or "hive ops devai" in lower:
            has_devai = True
        if "hive ops final" in lower or rel.endswith("bin/hive"):
            has_final = True
        if ".bashrc" in lower or ".zshrc" in lower:
            has_bashrc = True
        if "termux" in lower and "boot" in lower:
            has_boot = True
        if entry["risk"] == MigrationRisk.NEVER_COPY.value and "credential" in entry["reason"]:
            has_base64_credential = True
        if p.is_symlink():
            has_symlink = True

    if has_base64_credential or has_bashrc or has_boot:
        legacy_status = LegacyStatus.LEGACY_UNSUPPORTED
        classification_reason = "Legacy installation contains non-migratable items (credentials, shell startup, or boot scripts)"
    elif has_devai and has_final:
        legacy_status = LegacyStatus.LEGACY_CONFLICT
        classification_reason = "Both DevAI and Final trees detected in legacy installation"
    elif has_devai:
        legacy_status = LegacyStatus.LEGACY_DETECTED
        classification_reason = "DevAI-based legacy installation detected"
    elif has_final:
        legacy_status = LegacyStatus.LEGACY_DETECTED
        classification_reason = "Final-tree-based legacy installation detected"
    elif safe_items or manual_review_items or never_copy_items:
        legacy_status = LegacyStatus.LEGACY_PARTIAL
        classification_reason = "Partial or unclassified legacy installation detected"
    else:
        legacy_status = LegacyStatus.UNKNOWN
        classification_reason = "Legacy path exists but contents are unclassified"

    return {
        "legacy_status": legacy_status.value,
        "legacy_root": str(primary_root),
        "classification_reason": classification_reason,
        "has_devai": has_devai,
        "has_final": has_final,
        "has_bashrc_modification": has_bashrc,
        "has_boot_modification": has_boot,
        "has_base64_credential": has_base64_credential,
        "has_symlink": has_symlink,
        "candidates": {label: str(root) for label, root in candidates},
        "safe_items": safe_items[:20],
        "manual_review_items": manual_review_items[:20],
        "never_copy_items": never_copy_items[:20],
    }


def build_migration_plan(
    home: Path | None = None,
    legacy_root_override: Path | None = None,
) -> MigrationPlan:
    """Build a non-executable migration plan from detected legacy state."""
    findings = detect_legacy_installation(home, legacy_root_override)
    status = LegacyStatus(findings["legacy_status"])

    safe = findings.get("safe_items", [])
    manual = findings.get("manual_review_items", [])
    never_copy = findings.get("never_copy_items", [])

    strategy = ""
    if status == LegacyStatus.NO_LEGACY_INSTALLATION:
        strategy = "No migration required."
    elif status == LegacyStatus.LEGACY_UNSUPPORTED:
        strategy = "Migration is unsupported without manual remediation of credentials/shell/boot items."
    elif status in (LegacyStatus.LEGACY_DETECTED, LegacyStatus.LEGACY_PARTIAL):
        strategy = (
            f"Manual review required. Safe files ({len(safe)}) may be copied after review. "
            f"Never-copy items ({len(never_copy)}) must be recreated or removed. "
            "Shell startup and boot changes must be re-applied through the new installer after activation."
        )
    elif status == LegacyStatus.LEGACY_CONFLICT:
        strategy = "Resolve DevAI/Final or multiple-root conflict before any migration."
    else:
        strategy = "Unknown legacy state; migration is blocked."

    return MigrationPlan(
        legacy_status=status,
        legacy_root=findings.get("legacy_root"),
        classification_reason=findings["classification_reason"],
        safe_items=safe,
        manual_review_items=manual,
        never_copy_items=never_copy,
        rollback_strategy=strategy,
    )
