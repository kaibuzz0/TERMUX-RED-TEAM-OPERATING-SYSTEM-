"""Hive OS unified logging subsystem."""

from __future__ import annotations

from runtime_logs.errors import LogConfigError, LogRuntimeError
from runtime_logs.permissions import secure_dir, secure_file
from runtime_logs.rotation import RotationPolicy, apply_retention, rotate, rotate_if_needed
from runtime_logs.service_logger import RuntimeLogger, ServiceLogger

__all__ = [
    "LogConfigError",
    "LogRuntimeError",
    "secure_dir",
    "secure_file",
    "RotationPolicy",
    "rotate",
    "rotate_if_needed",
    "apply_retention",
    "ServiceLogger",
    "RuntimeLogger",
]
