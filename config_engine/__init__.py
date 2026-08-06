"""Unified Configuration Engine for Hive OS.

The Configuration Engine is the single authority for all subsystem configuration.
No subsystem should read configuration files directly after Milestone 14.
"""

from __future__ import annotations

from config_engine.config import ConfigEngine, get_config
from config_engine.schema import ConfigSchema, SchemaRegistry
from config_engine.errors import ConfigError, ConfigValidationError, ConfigTransactionError

__all__ = [
    "ConfigEngine",
    "ConfigSchema",
    "ConfigValidationError",
    "ConfigTransactionError",
    "SchemaRegistry",
    "get_config",
]

__version__ = "1.0.0"
