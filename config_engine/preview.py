"""Dry-run preview output formatting."""

from __future__ import annotations

import json
from typing import Any

from config_engine.merger import strip_internal_keys
from config_engine.transactions import PreviewResult


def format_preview(preview: PreviewResult, as_json: bool = True) -> str:
    """Format a preview result for CLI or API consumption."""
    payload = {
        "valid": preview.valid,
        "warnings": preview.warnings,
        "errors": preview.errors,
        "migration_effects": preview.migration_effects,
        "before": strip_internal_keys(preview.before),
        "after": strip_internal_keys(preview.after),
    }
    if as_json:
        return json.dumps(payload, indent=2, default=str)
    lines = []
    lines.append(f"Preview valid: {preview.valid}")
    if preview.errors:
        lines.append("Errors:")
        for e in preview.errors:
            lines.append(f"  - {e.get('field', '')}: {e.get('message', '')}")
    if preview.warnings:
        lines.append("Warnings:")
        for w in preview.warnings:
            lines.append(f"  - {w.get('field', '')}: {w.get('message', '')}")
    if preview.migration_effects:
        lines.append("Migration effects:")
        for m in preview.migration_effects:
            lines.append(f"  - {m}")
    return "\n".join(lines)
