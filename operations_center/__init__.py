"""Hive OS Operations Center."""

from __future__ import annotations

__all__ = ["main"]

# Lazy CLI import to avoid runpy RuntimeWarning when used as a module target.
def main(*args, **kwargs):
    from operations_center.cli import main as _cli_main
    return _cli_main(*args, **kwargs)
