"""Policy Engine errors."""

from __future__ import annotations


class PolicyError(Exception):
    """Base Policy Engine error."""


class PolicyValidationError(PolicyError):
    """Raised when a policy, request, or rule is invalid."""


class PolicyEvaluationError(PolicyError):
    """Raised when evaluation cannot be completed safely."""


class PolicyRequestError(PolicyError):
    """Raised when a policy request is malformed or unsupported."""


class PolicyNotFoundError(PolicyError):
    """Raised when a requested policy resource is missing."""


class PolicyPrecedenceError(PolicyError):
    """Raised when rule precedence is violated."""
