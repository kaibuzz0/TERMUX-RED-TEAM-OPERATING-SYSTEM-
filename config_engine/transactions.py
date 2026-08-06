"""Configuration transaction lifecycle: load, validate, preview, stage, commit, rollback."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_engine.errors import ConfigTransactionError, ConfigValidationError
from config_engine.loader import atomic_write_json
from config_engine.persistence import ConfigurationStore


@dataclass
class PreviewResult:
    """Result of a configuration preview/dry-run."""

    before: dict[str, Any]
    after: dict[str, Any]
    warnings: list[dict]
    errors: list[dict]
    migration_effects: list[str]
    valid: bool


class TransactionManager:
    """Manages atomic configuration transactions."""

    def __init__(self, store: ConfigurationStore, validate_fn: CallableFactory | None = None):
        self.store = store
        self._validate = validate_fn

    def preview(
        self,
        previous: dict[str, Any] | None,
        candidate: dict[str, Any],
    ) -> PreviewResult:
        """Show what would change without persisting anything."""
        before = previous or {}
        warnings = candidate.get("_warnings", [])
        migration_effects = candidate.get("_migration_performed", [])

        if self._validate is None:
            return PreviewResult(
                before=before,
                after=candidate,
                warnings=warnings,
                errors=[],
                migration_effects=migration_effects,
                valid=True,
            )

        try:
            validated = self._validate(candidate)
            return PreviewResult(
                before=before,
                after=validated,
                warnings=validated.get("_warnings", warnings),
                errors=[],
                migration_effects=migration_effects,
                valid=True,
            )
        except ConfigValidationError as e:
            return PreviewResult(
                before=before,
                after=candidate,
                warnings=warnings,
                errors=e.details or [{"message": str(e)}],
                migration_effects=migration_effects,
                valid=False,
            )

    def stage(self, candidate: dict[str, Any]) -> Path:
        """Stage a candidate configuration for review."""
        return self.store.create_staging(candidate)

    def commit(
        self,
        candidate: dict[str, Any],
        profile: str,
        author: str,
        migration_performed: list[str],
    ) -> dict[str, Any]:
        """Atomically commit a validated configuration."""
        previous = self.store.load_committed()
        preview = self.preview(previous, candidate)
        if not preview.valid:
            raise ConfigTransactionError(
                f"Cannot commit invalid configuration: {preview.errors}"
            )

        txn_id = self.store.archive_transaction(
            previous=previous,
            new=candidate,
            profile=profile,
            author=author,
            validation_result="ok",
            migration_performed=migration_performed,
        )
        self.store.save_committed(candidate)
        self.store.clear_staging()
        return {
            "transaction_id": txn_id,
            "profile": profile,
            "author": author,
            "timestamp": time.time(),
            "version": candidate.get("_meta", {}).get("version"),
        }

    def rollback(self, txn_id: str, author: str) -> dict[str, Any]:
        """Rollback to a historical transaction; creates a new transaction."""
        new_txn_id, target = self.store.rollback_to(txn_id, author)
        return {
            "transaction_id": new_txn_id,
            "restored_transaction": txn_id,
            "profile": target.get("_meta", {}).get("profile", "unknown"),
            "author": author,
            "timestamp": time.time(),
        }


class CallableFactory:
    """Type helper for validate callback."""

    def __init__(self, fn: Any):
        self.fn = fn

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.fn(data)
