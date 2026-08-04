"""Installation plan and journal schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional


class InstallStatus(Enum):
    CLEAN_INSTALL = "clean_install"
    MANAGED_UPGRADE_REQUIRED = "managed_upgrade_required"
    LEGACY_MIGRATION_REQUIRED = "legacy_migration_required"
    RECOVERY_REQUIRED = "recovery_required"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class CapabilityState(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"


class PackageCategory(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    UNSUPPORTED = "unsupported"
    ALREADY_AVAILABLE = "already_available"
    UNKNOWN = "unknown"


@dataclass
class TargetPolicy:
    root: Path
    config_root: Path
    state_root: Path
    data_root: Path
    cache_root: Path
    log_root: Path
    staging_root: Path


@dataclass
class SourceInfo:
    repository: Path
    remote: str
    commit: str
    canonical_source: Path
    launcher: Path


@dataclass
class Operation:
    op_id: str
    op_type: str
    source: Optional[Path] = None
    destination: Optional[Path] = None
    overwrite: bool = False


@dataclass
class InstallPlan:
    schema_version: int = 1
    transaction_id: str = ""
    source: SourceInfo = field(default_factory=lambda: SourceInfo(Path(), "", "", Path(), Path()))
    target: TargetPolicy = field(default_factory=lambda: TargetPolicy(Path(), Path(), Path(), Path(), Path(), Path(), Path()))
    operations: list[Operation] = field(default_factory=list)
    network_required: bool = False
    rollback_required: bool = True
    rollback_operations: list[Operation] = field(default_factory=list)
    existing_status: InstallStatus = InstallStatus.UNKNOWN
    required_packages: list[dict[str, Any]] = field(default_factory=list)
    proposed_shell_startup_entries: list[str] = field(default_factory=list)


def plan_to_dict(plan: InstallPlan) -> dict:
    """Serialize plan to a deterministic dictionary."""

    return {
        "schema_version": plan.schema_version,
        "transaction_id": plan.transaction_id,
        "source": {
            "repository": str(plan.source.repository),
            "remote": plan.source.remote,
            "commit": plan.source.commit,
            "canonical_source": str(plan.source.canonical_source),
            "launcher": str(plan.source.launcher),
        },
        "target": {
            "root": str(plan.target.root),
            "config_root": str(plan.target.config_root),
            "state_root": str(plan.target.state_root),
            "data_root": str(plan.target.data_root),
            "cache_root": str(plan.target.cache_root),
            "log_root": str(plan.target.log_root),
            "staging_root": str(plan.target.staging_root),
        },
        "operations": [
            {
                "id": op.op_id,
                "type": op.op_type,
                "source": str(op.source) if op.source else None,
                "destination": str(op.destination) if op.destination else None,
                "overwrite": op.overwrite,
            }
            for op in plan.operations
        ],
        "network_required": plan.network_required,
        "rollback_required": plan.rollback_required,
        "rollback_operations": [
            {
                "id": op.op_id,
                "type": op.op_type,
                "source": str(op.source) if op.source else None,
                "destination": str(op.destination) if op.destination else None,
                "overwrite": op.overwrite,
            }
            for op in plan.rollback_operations
        ],
        "existing_status": plan.existing_status.value,
        "required_packages": plan.required_packages,
        "proposed_shell_startup_entries": plan.proposed_shell_startup_entries,
    }
