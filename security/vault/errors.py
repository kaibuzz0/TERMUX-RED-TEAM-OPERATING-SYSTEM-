"""Vault-specific exceptions."""

from __future__ import annotations


class VaultError(Exception):
    """Base vault exception."""


class VaultLockedError(VaultError):
    """Operation requires an unlocked vault."""


class VaultCorruptError(VaultError):
    """Vault file is corrupt or tampered with."""


class VaultSafetyError(VaultError):
    """A safety or containment check failed."""


class VaultFormatError(VaultError):
    """Unsupported or malformed vault format."""


class VaultExistsError(VaultError):
    """Vault already exists and overwrite was not allowed."""
