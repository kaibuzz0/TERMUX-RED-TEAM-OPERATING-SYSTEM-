"""Update and recovery errors."""

from __future__ import annotations


class UpdateError(Exception):
    """Base update/recovery error."""


class TrustError(UpdateError):
    """Trust, signature, or verification failure."""


class BundleError(UpdateError):
    """Malformed or unsafe bundle."""


class CompatibilityError(UpdateError):
    """Release incompatible with current system."""


class RollbackError(UpdateError):
    """Rollback operation failure."""


class AntiRollbackError(UpdateError):
    """Security sequence or revocation failure."""


class NoVerifiedRuntime(UpdateError):
    """No verified runtime available for operation."""
