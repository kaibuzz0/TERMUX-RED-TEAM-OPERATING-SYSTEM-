"""Redaction and sanitization for Operations Center output."""

from __future__ import annotations

import re
from typing import Any


_SECRET_KEYWORDS = ("password", "secret", "key", "token", "nonce", "salt", "ciphertext", "private")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def redact_value(value: Any, path: str = "") -> Any:
    """Redact sensitive values and sanitize strings."""
    if isinstance(value, dict):
        return {k: redact_value(v, f"{path}.{k}" if path else k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v, f"{path}[]") for v in value]
    if isinstance(value, str):
        lower = value.lower()
        if any(kw in lower for kw in _SECRET_KEYWORDS) and len(value) > 4:
            return "***REDACTED***"
        return _CONTROL_RE.sub("?", value)
    return value


def redact_paths(value: Any) -> Any:
    """Replace full local paths with classification labels where appropriate."""
    if isinstance(value, dict):
        return {k: redact_paths(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_paths(v) for v in value]
    if isinstance(value, str) and value.startswith("/data/data/"):
        return "<TERMUX_PRIVATE_PATH>"
    return value
