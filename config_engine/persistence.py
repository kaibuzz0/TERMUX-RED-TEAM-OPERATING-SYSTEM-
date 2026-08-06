"""Configuration persistence layer."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from config_engine.errors import ConfigNotFoundError, ConfigTransactionError, ConfigValidationError

import errno
import time


class FileLock:
    """Simple cross-platform advisory file lock using lockfile directory."""

    def __init__(self, lock_path: Path, timeout: float = 5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self._held = False

    def __enter__(self):
        start = time.time()
        while True:
            try:
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                self.lock_path.mkdir()
                self._held = True
                return self
            except FileExistsError:
                if time.time() - start > self.timeout:
                    raise ConfigTransactionError(f"Could not acquire lock: {self.lock_path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc, tb):
        if self._held:
            try:
                self.lock_path.rmdir()
            except OSError:
                pass
            self._held = False


def acquire_config_lock(state_root: Path) -> FileLock:
    return FileLock(state_root / ".config_lock")

from config_engine.loader import atomic_write_json, load_config_file


class ConfigurationStore:
    """Filesystem-backed store for committed configuration and history."""

    def __init__(self, config_root: Path, state_root: Path):
        self.config_root = config_root
        self.state_root = state_root
        self.committed_path = config_root / "config.json"
        self.history_dir = state_root / "config_history"
        self.staging_dir = state_root / "config_staging"

    def ensure_dirs(self) -> None:
        self.config_root.mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def load_committed(self) -> dict[str, Any] | None:
        """Load the currently committed configuration, if any."""
        if not self.committed_path.exists():
            return None
        return load_config_file(self.committed_path)

    def save_committed(self, data: dict[str, Any]) -> None:
        """Persist committed configuration atomically."""
        self.ensure_dirs()
        with acquire_config_lock(self.state_root):
            atomic_write_json(self.committed_path, data)

    def create_staging(self, data: dict[str, Any]) -> Path:
        """Create a staged configuration file and return its path."""
        self.ensure_dirs()
        stage_id = f"stage-{uuid.uuid4().hex}"
        stage_path = self.staging_dir / f"{stage_id}.json"
        atomic_write_json(stage_path, data)
        return stage_path

    def clear_staging(self) -> None:
        """Remove all staged configuration files."""
        if not self.staging_dir.exists():
            return
        for path in self.staging_dir.glob("*.json"):
            path.unlink()

    def archive_transaction(
        self,
        previous: dict[str, Any] | None,
        new: dict[str, Any],
        profile: str,
        author: str,
        validation_result: str,
        migration_performed: list[str],
    ) -> str:
        """Archive a committed configuration as a new transaction."""
        self.ensure_dirs()
        txn_id = f"txn-{uuid.uuid4().hex}"
        with acquire_config_lock(self.state_root):
            snapshot_path = self.history_dir / f"{txn_id}.json"
            atomic_write_json(snapshot_path, new)
            record = {
                "transaction_id": txn_id,
                "previous_version": previous.get("_meta", {}).get("version") if previous else None,
                "new_version": new.get("_meta", {}).get("version"),
                "profile": profile,
                "author": author,
                "timestamp": time.time(),
                "validation_result": validation_result,
                "migration_performed": migration_performed,
                "rollback_available": True,
                "snapshot_path": str(snapshot_path),
            }
            record_path = self.history_dir / f"{txn_id}.record.json"
            atomic_write_json(record_path, _redact_record(record))
        return txn_id

    def load_transaction(self, txn_id: str) -> dict[str, Any]:
        """Load a historical transaction snapshot."""
        snapshot_path = self.history_dir / f"{txn_id}.json"
        if not snapshot_path.exists():
            raise ConfigNotFoundError(f"Transaction not found: {txn_id}")
        return load_config_file(snapshot_path)

    def load_transaction_record(self, txn_id: str) -> dict[str, Any]:
        """Load the metadata record for a transaction."""
        record_path = self.history_dir / f"{txn_id}.record.json"
        if not record_path.exists():
            raise ConfigNotFoundError(f"Transaction record not found: {txn_id}")
        return load_config_file(record_path)

    def list_transactions(self) -> list[dict[str, Any]]:
        """Return all transaction records in chronological order."""
        if not self.history_dir.exists():
            return []
        records = []
        for path in sorted(self.history_dir.glob("*.record.json")):
            try:
                records.append(load_config_file(path))
            except (ConfigNotFoundError, ConfigValidationError, OSError):
                continue
        return records

    def rollback_to(self, txn_id: str, author: str) -> tuple[str, dict[str, Any]]:
        """Rollback to a historical transaction snapshot, creating a new transaction."""
        target = self.load_transaction(txn_id)
        new_txn_id = self.archive_transaction(
            previous=self.load_committed(),
            new=target,
            profile=target.get("_meta", {}).get("profile", "unknown"),
            author=author,
            validation_result="rollback",
            migration_performed=[],
        )
        self.save_committed(target)
        return new_txn_id, target


def _redact_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove any secret-like fields from audit records."""
    redacted = dict(record)
    for key in list(redacted.keys()):
        lower = key.lower()
        if any(s in lower for s in ("secret", "password", "key", "token", "credential")):
            redacted[key] = "[REDACTED]"
    return redacted
