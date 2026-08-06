"""Configuration engine errors."""

from __future__ import annotations


class ConfigError(Exception):
    """Base Configuration Engine error."""


class ConfigValidationError(ConfigError):
    """Raised when configuration fails schema validation."""

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.details = details or []


class ConfigTransactionError(ConfigError):
    """Raised when a configuration transaction cannot be applied."""


class ConfigMigrationError(ConfigError):
    """Raised when a configuration migration fails."""


class ConfigProfileError(ConfigError):
    """Raised when profile loading or inheritance fails."""


class ConfigRollbackError(ConfigError):
    """Raised when rollback cannot be completed."""


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file or transaction is missing."""
