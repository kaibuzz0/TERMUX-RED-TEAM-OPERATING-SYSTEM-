"""Installation plan, activation, and journal schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


class ActivationState(Enum):
    """Lifecycle states for a staged release before, during, and after activation."""

    STAGED = "staged"
    VERIFIED = "verified"
    READY_TO_ACTIVATE = "ready_to_activate"
    ACTIVE = "active"
    ACTIVATION_FAILED = "activation_failed"
    ROLLBACK_AVAILABLE = "rollback_available"
    ROLLED_BACK = "rolled_back"


class LegacyStatus(Enum):
    """Classification of legacy installation presence."""

    NO_LEGACY_INSTALLATION = "no_legacy_installation"
    LEGACY_DETECTED = "legacy_detected"
    LEGACY_CONFLICT = "legacy_conflict"
    LEGACY_PARTIAL = "legacy_partial"
    LEGACY_UNSUPPORTED = "legacy_unsupported"
    UNKNOWN = "unknown"


class MigrationRisk(Enum):
    """Risk classification for items in a migration plan."""

    SAFE = "safe"
    MANUAL_REVIEW = "manual_review"
    NEVER_COPY = "never_copy"
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


@dataclass
class ReleaseInfo:
    """Metadata for a single versioned release under the data root."""

    release_id: str
    transaction_id: str
    state: ActivationState
    repository: str
    commit: str
    canonical_source: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    manifest_digest: str = ""
    previous_release_id: str = ""


@dataclass
class ActivePointer:
    """Pointer to the currently active release."""

    active_release_id: str
    active_runtime: str
    previous_release_id: str
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MigrationPlan:
    """Non-executable migration plan from a legacy installation."""

    legacy_status: LegacyStatus
    legacy_root: Optional[str]
    classification_reason: str
    safe_items: list[dict[str, Any]] = field(default_factory=list)
    manual_review_items: list[dict[str, Any]] = field(default_factory=list)
    never_copy_items: list[dict[str, Any]] = field(default_factory=list)
    rollback_strategy: str = ""


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


def release_to_dict(release: ReleaseInfo, metadata: dict[str, Any] | None = None, trust_level: str | None = None) -> dict:
    data = {
        "schema_version": 1,
        "release_id": release.release_id,
        "transaction_id": release.transaction_id,
        "state": release.state.value,
        "repository": release.repository,
        "commit": release.commit,
        "canonical_source": release.canonical_source,
        "created_at": release.created_at,
        "manifest_digest": release.manifest_digest,
        "previous_release_id": release.previous_release_id,
    }
    if metadata:
        data["metadata"] = metadata
    if trust_level:
        data["trust_level"] = trust_level
    return data


def active_pointer_to_dict(pointer: ActivePointer) -> dict:
    return {
        "schema_version": 1,
        "active_release_id": pointer.active_release_id,
        "active_runtime": pointer.active_runtime,
        "previous_release_id": pointer.previous_release_id,
        "updated_at": pointer.updated_at,
    }


def migration_plan_to_dict(plan: MigrationPlan) -> dict:
    return {
        "schema_version": 1,
        "legacy_status": plan.legacy_status.value,
        "legacy_root": plan.legacy_root,
        "classification_reason": plan.classification_reason,
        "safe_items": plan.safe_items,
        "manual_review_items": plan.manual_review_items,
        "never_copy_items": plan.never_copy_items,
        "rollback_strategy": plan.rollback_strategy,
    }
