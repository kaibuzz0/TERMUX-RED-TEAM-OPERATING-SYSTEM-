"""Secret redaction helpers."""

from __future__ import annotations

import re
from typing import Any


_SECRET_KEYS = {
    "password",
    "passwd",
    "pin",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "auth",
    "private_key",
    "privatekey",
    "master_key",
    "key",
    "ciphertext",
    "salt",
    "nonce",
    "derived_key",
}

_TOKEN_LIKE = re.compile(r"[A-Za-z0-9_\-]{32,}")


def redact(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with known secret values replaced."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = redact(v)
        elif isinstance(v, list):
            result[k] = [_redact_item(i) for i in v]
        elif isinstance(v, (str, bytes)):
            result[k] = _redact_value(k, v)
        else:
            result[k] = v
    return result


def _redact_item(item: Any) -> Any:
    if isinstance(item, dict):
        return redact(item)
    if isinstance(item, (str, bytes)):
        return _redact_value("", item)
    return item


def _redact_value(key: str, value: Any) -> str:
    if not isinstance(value, (str, bytes)):
        return value
    text = value.decode("utf-8") if isinstance(value, bytes) else value
    if key.lower() in _SECRET_KEYS:
        return "[REDACTED]"
    if _TOKEN_LIKE.fullmatch(text) and len(text) >= 32:
        return "[REDACTED]"
    return text


def redact_exception(exc: BaseException) -> str:
    """Return exception text with plausible secret values redacted."""
    text = str(exc)
    for word in _TOKEN_LIKE.findall(text):
        if len(word) >= 32:
            text = text.replace(word, "[REDACTED]")
    return text
