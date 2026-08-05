"""Typed broker errors."""

from __future__ import annotations


class BrokerError(Exception):
    """Base broker error."""


class ManifestError(BrokerError):
    """Invalid task manifest."""


class CapabilityError(BrokerError):
    """Required capability not available."""


class PolicyError(BrokerError):
    """Action not permitted by active policy."""


class ApprovalError(BrokerError):
    """Approval missing, expired, or invalid."""


class DispatchError(BrokerError):
    """Failed to dispatch to subsystem."""


class TransactionError(BrokerError):
    """Invalid transaction state."""


class SessionError(BrokerError):
    """Invalid session state."""


class AuditError(BrokerError):
    """Audit write failed."""
