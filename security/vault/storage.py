"""Atomic vault storage with containment checks."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from security.vault.errors import VaultSafetyError


class VaultStorage:
    """Manages the on-disk vault file location and atomic writes."""

    VAULT_FILE_NAME = "vault.json"

    def __init__(self, vault_dir: Path):
        self.vault_dir = vault_dir
        self.vault_path = vault_dir / self.VAULT_FILE_NAME

    def _ensure_contained(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self.vault_dir.resolve())
        except ValueError:
            raise VaultSafetyError(f"Vault path escapes vault directory: {path}")

    def exists(self) -> bool:
        return self.vault_path.exists()

    def read(self) -> str:
        if not self.exists():
            raise VaultSafetyError("Vault does not exist")
        return self.vault_path.read_text(encoding="utf-8")

    def write(self, payload: str, overwrite: bool = False) -> None:
        if self.vault_path.exists() and not overwrite:
            from security.vault.errors import VaultExistsError
            raise VaultExistsError("Vault already exists; use overwrite=True to replace")

        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_contained(self.vault_path)

        tmp = self.vault_path.with_suffix(".tmp")
        self._ensure_contained(tmp)

        tmp.write_text(payload, encoding="utf-8")
        try:
            os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        tmp.replace(self.vault_path)

    def backup(self) -> Path:
        if not self.exists():
            raise VaultSafetyError("No vault to back up")
        backup = self.vault_path.with_suffix(".backup")
        self._ensure_contained(backup)
        backup.write_text(self.vault_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup
