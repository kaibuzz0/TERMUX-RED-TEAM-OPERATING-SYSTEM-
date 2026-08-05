"""Terminal and JSON rendering for Operations Center."""

from __future__ import annotations

import json
import re
from typing import Any

from operations_center.redaction import redact_value


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def render_json(data: dict[str, Any]) -> str:
    safe = redact_value(data)
    return json.dumps(safe, indent=2, default=str)


def render_text(data: dict[str, Any], compact: bool = False, width: int = 80, no_color: bool = True) -> str:
    view = data.get("view", "unknown")
    lines = [
        "=" * min(40, width),
        f"Hive OS Operations Center — {view}",
        f"Snapshot: {data.get('snapshot_id')} | Status: {data.get('status')}",
        f"Generated: {data.get('generated_at')}",
        "=" * min(40, width),
    ]

    if view == "overview":
        d = data.get("data", {})
        lines.extend([
            f"Version:        {d.get('hive_version') or 'unknown'}",
            f"Platform:       {d.get('runtime_platform') or 'unknown'}",
            f"Broker:         {d.get('broker_version') or 'unknown'} (available={d.get('broker_available')})",
            f"Services:       running={d.get('services_running')}/{d.get('service_total')} failed={d.get('services_failed')} crash_loop={d.get('critical_count')}",
            f"Vault state:    {d.get('vault_state')}",
            f"Update:         {d.get('update_active_release') or 'unknown'}",
            f"Recovery:       {d.get('recovery_status')}",
            f"Diagnostics:    {d.get('diagnostic_count')} total, {d.get('warning_count')} warning+, {d.get('critical_count')} critical",
            f"Validation:     {d.get('physical_validation')}",
        ])

    sources = data.get("sources", {})
    if sources and not compact:
        lines.append("Sources:")
        for name, info in sources.items():
            lines.append(f"  {name}: {info.get('status')} ({info.get('duration_ms', 0)}ms)")

    diagnostics = data.get("diagnostics", [])
    if diagnostics:
        lines.append("Diagnostics:")
        for diag in diagnostics:
            lines.append(f"  [{diag.get('severity')}] {diag.get('code')}: {diag.get('message')}")

    errors = data.get("errors", [])
    if errors:
        lines.append("Errors:")
        for err in errors:
            lines.append(f"  - {_CONTROL_RE.sub('?', err)}")

    lines.append("=" * min(40, width))
    return "\n".join(lines)
