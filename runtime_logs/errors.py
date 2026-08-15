"""Logging subsystem errors."""

from __future__ import annotations


class LogConfigError(Exception):
    """Invalid logging configuration."""


class LogRuntimeError(Exception):
    """Logging runtime failure."""
