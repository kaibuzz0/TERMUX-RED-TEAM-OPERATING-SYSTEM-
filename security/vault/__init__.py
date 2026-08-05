"""Hive OS encrypted vault package."""

from __future__ import annotations

from security.vault.backend import Vault
from security.vault.session import VaultSession
from security.vault.migration import detect_legacy_credentials, build_migration_plan
from security.vault.errors import VaultError, VaultLockedError, VaultCorruptError, VaultSafetyError

__all__ = [
    "Vault",
    "VaultSession",
    "detect_legacy_credentials",
    "build_migration_plan",
    "VaultError",
    "VaultLockedError",
    "VaultCorruptError",
    "VaultSafetyError",
]
