"""Service supervisor errors."""

from __future__ import annotations


class ServiceError(Exception):
    """Base supervisor error."""


class ServiceConfigError(ServiceError):
    """Malformed or unsafe service manifest."""


class ServiceRuntimeError(ServiceError):
    """Runtime supervision failure."""


class ServiceDependencyError(ServiceError):
    """Dependency ordering or missing dependency."""


class ServiceStateError(ServiceError):
    """State or lock issue."""
