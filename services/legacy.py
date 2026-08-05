"""Non-mutating legacy `.svc` adapter and migration planner."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from services.errors import ServiceConfigError


DANGEROUS_PATTERNS = [
    ("command_substitution", re.compile(r"\$\(|`[^`]*`")),
    ("pipeline", re.compile(r"\|\|?")),
    ("redirection", re.compile(r"[><]|>>")),
    ("dynamic_sourcing", re.compile(r"\.\s+\$|source\s+\$"),),
    ("broad_kill", re.compile(r"pkill|killall")),
    ("remote_download", re.compile(r"curl|wget")),
    ("privilege_escalation", re.compile(r"\bsudo\b|su\s+-"),),
]

SAFE_VARS = {"START", "PROBE", "LOG", "REQUIRES_NET", "USE_PROXY_ENV", "WANT_TORSOCKS"}


def parse_svc_file(path: Path) -> dict[str, Any]:
    """Parse a legacy `.svc` file textually, without sourcing or executing it."""
    text = path.read_text(encoding="utf-8", errors="replace")
    assignments: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in SAFE_VARS:
                assignments[key] = value

    classification = _classify(assignments)
    return {
        "source": str(path),
        "name": path.stem,
        "assignments": assignments,
        "classification": classification,
        "safe_to_translate": classification == "SAFE_TO_TRANSLATE",
    }


def _classify(assignments: dict[str, str]) -> str:
    start = assignments.get("START", "")
    probe = assignments.get("PROBE", "")
    for label, pattern in DANGEROUS_PATTERNS:
        if pattern.search(start) or pattern.search(probe):
            return "UNSUPPORTED_SHELL" if label in ("command_substitution", "pipeline", "redirection", "dynamic_sourcing") else "DANGEROUS"
    # Simple single command strings are reviewable.
    return "REQUIRES_REVIEW"


def build_migration_plan(path: Path) -> dict[str, Any]:
    parsed = parse_svc_file(path)
    return {
        "original": str(path),
        "service_name": parsed["name"],
        "start": parsed["assignments"].get("START"),
        "probe": parsed["assignments"].get("PROBE"),
        "log": parsed["assignments"].get("LOG"),
        "requires_net": parsed["assignments"].get("REQUIRES_NET", "1"),
        "use_proxy_env": parsed["assignments"].get("USE_PROXY_ENV", "0"),
        "want_torsocks": parsed["assignments"].get("WANT_TORSOCKS", "0"),
        "classification": parsed["classification"],
        "target_native_manifest": None,
        "manual_review_fields": ["START", "PROBE", "LOG", "REQUIRES_NET", "USE_PROXY_ENV", "WANT_TORSOCKS"],
        "rollback_plan": "Restore original `.svc` and use legacy `hive_services.sh`.",
    }
