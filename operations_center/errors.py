"""Operations Center errors."""

from __future__ import annotations


class OperationsCenterError(Exception):
    """Base error."""


class ViewError(OperationsCenterError):
    """View assembly failed."""
