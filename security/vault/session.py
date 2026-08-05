"""Vault session lifecycle and CLI-facing state."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from security.vault.backend import Vault
from security.vault.errors import VaultError, VaultLockedError


class SessionState(Enum):
    UNINITIALIZED = "uninitialized"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    CORRUPT = "corrupt"
    MIGRATION_REQUIRED = "migration_required"


class VaultSession:
    """Operator-facing vault session with bounded unlock attempts."""

    MAX_ATTEMPTS = 5

    def __init__(self, vault_dir: Path | None = None):
        self.vault = Vault(vault_dir)
        self.state = SessionState.UNINITIALIZED
        self._failed_attempts = 0
        self._refresh_state()

    def locked(self) -> bool:
        return self.vault.locked()

    def _refresh_state(self) -> None:
        if self.vault.storage.exists():
            try:
                if self.vault.locked():
                    self.state = SessionState.LOCKED
                else:
                    self.state = SessionState.UNLOCKED
            except Exception:
                self.state = SessionState.CORRUPT
        else:
            self.state = SessionState.UNINITIALIZED

    def init(self, master_password: str) -> None:
        self.vault.init(master_password)
        self._refresh_state()

    def unlock(self, master_password: str) -> None:
        if self._failed_attempts >= self.MAX_ATTEMPTS:
            raise VaultError("Too many failed unlock attempts; session disabled")
        try:
            self.vault.unlock(master_password)
            self._failed_attempts = 0
            self.state = SessionState.UNLOCKED
        except Exception as e:
            self._failed_attempts += 1
            self.vault.lock()
            self.state = SessionState.LOCKED
            raise VaultError(f"Unlock failed: {e}") from e

    def lock(self) -> None:
        self.vault.lock()
        self.state = SessionState.LOCKED

    def status(self) -> dict[str, Any]:
        result = self.vault.status()
        result["session_state"] = self.state.value
        result["failed_attempts"] = self._failed_attempts
        result["max_attempts"] = self.MAX_ATTEMPTS
        return result
