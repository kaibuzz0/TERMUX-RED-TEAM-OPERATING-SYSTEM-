"""Controlled activation, rollback, and active-runtime management."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config_engine.persistence import FileLock
from config_engine.errors import ConfigTransactionError

from installer.journal import InstallJournal
from installer.schema import (
    ActivationState,
    ActivePointer,
    InstallPlan,
    ReleaseInfo,
    release_to_dict,
    active_pointer_to_dict,
)
from installer.verify import verify_staged_manifest


class ActivationError(Exception):
    """Activation or rollback failure."""


class ActivationSafetyError(ActivationError):
    """A safety invariant blocked activation."""


class ActiveState:
    """Manages the versioned active runtime layout under the data root.

    Layout:
      $HIVE_DATA_ROOT/
        releases/
          <release_id>/
            runtime/
            .release.json
        active.json
        .lock

    The active pointer is a small JSON file rather than a symlink by default,
    because symlink support cannot be assumed on all target filesystems.
    """

    ACTIVE_POINTER_SCHEMA_VERSION = 1
    RELEASE_SCHEMA_VERSION = 1

    def __init__(self, data_root: Path, state_root: Path, transaction_id: str | None = None):
        self.data_root = data_root
        self.state_root = state_root
        self.releases_dir = data_root / "releases"
        self.active_pointer_path = data_root / "active.json"
        self.lock_path = state_root / ".install-lock"
        self._dirlock_path = state_root / ".install-lock.dir"
        self.transaction_id = transaction_id
        self._file_lock = None

    # ------------------------------------------------------------------
    # Lock helpers
    # ------------------------------------------------------------------
    def _read_lock(self) -> dict[str, Any] | None:
        if not self.lock_path.exists():
            return None
        try:
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"transaction_id": None, "stale": True}

    def _write_lock(self, transaction_id: str) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(
            json.dumps({"transaction_id": transaction_id, "created_at": _utc_now()}),
            encoding="utf-8",
        )

    def _remove_lock(self) -> None:
        if self.lock_path.exists():
            self.lock_path.unlink()

    def _is_stale_lock(self, lock: dict[str, Any]) -> bool:
        return bool(lock.get("stale"))

    def acquire_lock(self, transaction_id: str, force: bool = False) -> None:
        """Acquire the installation transaction lock using atomic FileLock."""
        if not force:
            # Use directory-based advisory lock for atomicity
            lock = FileLock(self._dirlock_path, timeout=10.0)
            try:
                lock.__enter__()
                self._file_lock = lock
            except ConfigTransactionError as e:
                # Lock held by another process — check if it's stale
                existing = self._read_lock()
                if existing and not self._is_stale_lock(existing):
                    current = existing.get("transaction_id")
                    raise ActivationSafetyError(
                        f"Installation lock held by transaction {current}; use --force-stale-lock to recover a stale lock"
                    ) from e
                # Stale lock — proceed to overwrite
                self._file_lock = lock
                self._file_lock.__enter__()

            # Now that we hold the FileLock, check for conflicting transaction
            existing = self._read_lock()
            if existing and not self._is_stale_lock(existing):
                current = existing.get("transaction_id")
                if current and current != transaction_id and not force:
                    # Release FileLock before raising
                    lock.__exit__(None, None, None)
                    self._file_lock = None
                    raise ActivationSafetyError(
                        f"Installation lock held by transaction {current}; use --force-stale-lock to recover a stale lock"
                    )

        # Write lock metadata for diagnostics
        self._write_lock(transaction_id)

    def release_lock(self) -> None:
        self._remove_lock()
        if self._file_lock is not None:
            self._file_lock.__exit__(None, None, None)
            self._file_lock = None

    def recover_stale_lock(self) -> dict[str, Any] | None:
        """Return stale lock contents and remove it. Caller must decide whether to proceed."""
        lock = self._read_lock()
        if lock is None:
            return None
        if not self._is_stale_lock(lock):
            return None
        self._remove_lock()
        return lock

    # ------------------------------------------------------------------
    # Pointer / release helpers
    # ------------------------------------------------------------------
    def _active_pointer(self) -> ActivePointer | None:
        if not self.active_pointer_path.exists():
            return None
        try:
            data = json.loads(self.active_pointer_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise ActivationSafetyError(f"Corrupt active pointer: {e}")
        if data.get("schema_version") != self.ACTIVE_POINTER_SCHEMA_VERSION:
            raise ActivationSafetyError("Unknown active pointer schema")
        return ActivePointer(
            active_release_id=data["active_release_id"],
            active_runtime=data["active_runtime"],
            previous_release_id=data.get("previous_release_id", ""),
            updated_at=data.get("updated_at", _utc_now()),
        )

    def _release_path(self, release_id: str) -> Path:
        return self.releases_dir / release_id

    def _release_metadata_path(self, release_id: str) -> Path:
        return self._release_path(release_id) / ".release.json"

    def _write_active_pointer(self, pointer: ActivePointer) -> None:
        tmp = self.active_pointer_path.with_suffix(".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(active_pointer_to_dict(pointer), indent=2), encoding="utf-8")
        tmp.replace(self.active_pointer_path)

    def _write_release_metadata(self, release: ReleaseInfo) -> None:
        path = self._release_metadata_path(release.release_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(release_to_dict(release), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _read_release_metadata(self, release_id: str) -> ReleaseInfo:
        path = self._release_metadata_path(release_id)
        if not path.exists():
            raise ActivationSafetyError(f"Release metadata missing: {release_id}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise ActivationSafetyError(f"Corrupt release metadata: {e}")
        if data.get("schema_version") != self.RELEASE_SCHEMA_VERSION:
            raise ActivationSafetyError("Unknown release metadata schema")
        return ReleaseInfo(
            release_id=data["release_id"],
            transaction_id=data["transaction_id"],
            state=ActivationState(data["state"]),
            repository=data["repository"],
            commit=data["commit"],
            canonical_source=data["canonical_source"],
            created_at=data["created_at"],
            manifest_digest=data.get("manifest_digest", ""),
            previous_release_id=data.get("previous_release_id", ""),
        )

    # ------------------------------------------------------------------
    # State machine transitions
    # ------------------------------------------------------------------
    def _validate_state_transition(self, release: ReleaseInfo, target: ActivationState) -> None:
        allowed = {
            ActivationState.STAGED: {ActivationState.VERIFIED, ActivationState.ACTIVATION_FAILED},
            ActivationState.VERIFIED: {ActivationState.READY_TO_ACTIVATE, ActivationState.ACTIVATION_FAILED},
            ActivationState.READY_TO_ACTIVATE: {ActivationState.ACTIVE, ActivationState.ACTIVATION_FAILED, ActivationState.ROLLED_BACK},
            ActivationState.ACTIVE: {ActivationState.ROLLBACK_AVAILABLE},
            ActivationState.ROLLBACK_AVAILABLE: {ActivationState.ROLLED_BACK, ActivationState.ACTIVE},
            ActivationState.ACTIVATION_FAILED: set(),
            ActivationState.ROLLED_BACK: set(),
        }
        if target not in allowed.get(release.state, set()):
            raise ActivationSafetyError(
                f"Invalid activation transition: {release.state.value} -> {target.value}"
            )

    # ------------------------------------------------------------------
    # Staging verification / promotion
    # ------------------------------------------------------------------
    def verify_stage(self, staging_root: Path) -> dict[str, Any]:
        """Verify a staged release. Does not mutate active state."""
        if not staging_root.is_absolute():
            raise ActivationSafetyError("Staging root must be absolute")
        result = verify_staged_manifest(staging_root)
        return result

    def promote_to_ready(self, staging_root: Path, plan: InstallPlan) -> ReleaseInfo:
        """Verify stage and copy it into the versioned releases directory as READY_TO_ACTIVATE."""
        result = self.verify_stage(staging_root)
        if not result["valid"]:
            raise ActivationSafetyError(
                f"Cannot promote unverified stage: {result['errors']}"
            )

        release_id = plan.transaction_id
        release_dir = self._release_path(release_id)
        runtime_dir = release_dir / "runtime"
        staged_runtime = staging_root / "data" / "runtime"

        if runtime_dir.exists():
            raise ActivationSafetyError(
                f"Release directory already exists; cannot overwrite: {release_id}"
            )

        self.acquire_lock(plan.transaction_id)
        try:
            runtime_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staged_runtime, runtime_dir)
            digest = self._manifest_digest(release_dir / "runtime")
            release = ReleaseInfo(
                release_id=release_id,
                transaction_id=plan.transaction_id,
                state=ActivationState.READY_TO_ACTIVATE,
                repository=str(plan.source.repository),
                commit=plan.source.commit,
                canonical_source=str(plan.source.canonical_source),
                manifest_digest=digest,
                previous_release_id="",
            )
            self._write_release_metadata(release)
            journal = InstallJournal(self.state_root / "install-journal", plan.transaction_id)
            journal.append("promote", "promote", {"release_id": release_id, "digest": digest}, result="completed")
            return release
        finally:
            self.release_lock()

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------
    def activate(
        self,
        release_id: str,
        approve: bool = False,
    ) -> ActivePointer:
        """Activate a READY_TO_ACTIVATE or VERIFIED release.

        Requires explicit approval unless the release is already ACTIVE.
        """
        if not approve:
            raise ActivationSafetyError(
                "Activation requires explicit approval (--approve). No production runtime is changed without it."
            )

        release = self._read_release_metadata(release_id)
        if release.state not in (ActivationState.READY_TO_ACTIVATE, ActivationState.VERIFIED):
            raise ActivationSafetyError(
                f"Release {release_id} is not ready to activate (state={release.state.value})"
            )

        self.acquire_lock(release.transaction_id)
        try:
            runtime_dir = self._release_path(release_id) / "runtime"
            if not runtime_dir.exists():
                raise ActivationSafetyError(f"Release runtime missing: {runtime_dir}")

            # Validate containment: runtime must live under data root.
            try:
                runtime_dir.resolve().relative_to(self.data_root.resolve())
            except ValueError:
                raise ActivationSafetyError("Release runtime escapes data root")

            previous = self._active_pointer()
            previous_release_id = previous.active_release_id if previous else ""

            # Idempotency: if already active, return existing pointer.
            if previous and previous.active_release_id == release_id:
                return previous

            pointer = ActivePointer(
                active_release_id=release_id,
                active_runtime=str(runtime_dir),
                previous_release_id=previous_release_id,
            )

            # Atomic pointer write; previous pointer is preserved via previous_release_id.
            self._write_active_pointer(pointer)

            # Update release state.
            release.state = ActivationState.ACTIVE
            release.previous_release_id = previous_release_id
            self._write_release_metadata(release)

            journal = InstallJournal(self.state_root / "install-journal", release.transaction_id)
            journal.append(
                "activate",
                "activate",
                {
                    "release_id": release_id,
                    "previous_release_id": previous_release_id,
                    "active_runtime": str(runtime_dir),
                },
                result="completed",
            )

            return pointer
        finally:
            self.release_lock()

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------
    def rollback(self, approve: bool = False) -> ActivePointer:
        """Roll back to the previous active release."""
        if not approve:
            raise ActivationSafetyError(
                "Rollback requires explicit approval (--approve)."
            )

        current = self._active_pointer()
        if not current:
            raise ActivationSafetyError("No active release to roll back from")

        previous_release_id = current.previous_release_id
        if not previous_release_id:
            raise ActivationSafetyError("No previous release available for rollback")

        previous = self._read_release_metadata(previous_release_id)
        if previous.state != ActivationState.ACTIVE:
            # After a rollback, the previous release may still be ACTIVE in metadata.
            # We require it was once ACTIVE (recorded state is ACTIVE or ROLLED_BACK).
            if previous.state not in (ActivationState.ACTIVE, ActivationState.ROLLED_BACK):
                raise ActivationSafetyError(
                    f"Previous release {previous_release_id} was not a verified active release"
                )

        self.acquire_lock(previous.transaction_id)
        try:
            previous_runtime = self._release_path(previous_release_id) / "runtime"
            if not previous_runtime.exists():
                raise ActivationSafetyError(f"Previous release runtime missing: {previous_runtime}")

            new_pointer = ActivePointer(
                active_release_id=previous_release_id,
                active_runtime=str(previous_runtime),
                previous_release_id=current.active_release_id,
            )
            self._write_active_pointer(new_pointer)

            current_release = self._read_release_metadata(current.active_release_id)
            current_release.state = ActivationState.ROLLBACK_AVAILABLE
            self._write_release_metadata(current_release)

            previous.state = ActivationState.ROLLED_BACK
            self._write_release_metadata(previous)

            journal = InstallJournal(self.state_root / "install-journal", previous.transaction_id)
            journal.append(
                "rollback",
                "rollback",
                {
                    "from_release_id": current.active_release_id,
                    "to_release_id": previous_release_id,
                },
                result="completed",
            )

            return new_pointer
        finally:
            self.release_lock()

    def status(self) -> dict[str, Any]:
        """Return current active-state summary."""
        pointer = self._active_pointer()
        lock = self._read_lock()
        releases = []
        if self.releases_dir.exists():
            for rel_path in sorted(self.releases_dir.iterdir()):
                if (rel_path / ".release.json").exists():
                    rel = self._read_release_metadata(rel_path.name)
                    releases.append(release_to_dict(rel))
        return {
            "active": active_pointer_to_dict(pointer) if pointer else None,
            "locked": lock is not None and not self._is_stale_lock(lock),
            "lock_holder": lock.get("transaction_id") if lock else None,
            "releases": releases,
            "data_root": str(self.data_root),
            "state_root": str(self.state_root),
        }

    def _manifest_digest(self, runtime_dir: Path) -> str:
        """Compute a stable digest of the staged runtime manifest."""
        manifest_path = runtime_dir.parent.parent / "state" / "manifest.json"
        if not manifest_path.exists():
            return ""
        h = hashlib.sha256()
        with open(manifest_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
