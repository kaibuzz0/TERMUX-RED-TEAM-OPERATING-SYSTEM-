"""Rollback preparation and execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from installer.schema import InstallPlan, Operation


class RollbackPlanner:
    """Generate a rollback plan from an installation plan or journal."""


    def __init__(self, plan: InstallPlan):
        self.plan = plan

    def prepare(self) -> list[dict[str, Any]]:
        """Return the rollback operation list as plain dicts."""
        return [
            {
                "id": op.op_id,
                "type": op.op_type,
                "destination": str(op.destination) if op.destination else None,
            }
            for op in self.plan.rollback_operations
        ]


def execute_rollback(rollback_ops: list[dict[str, Any]], journal_path: Path | None = None) -> None:
    """Execute rollback operations in reverse order. (Milestone 6: only called in tests.)"""
    import shutil
    from installer.journal import InstallJournal

    for op in reversed(rollback_ops):
        dest = op.get("destination")
        if not dest:
            continue
        p = Path(dest)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        # Journal handled by caller normally.
