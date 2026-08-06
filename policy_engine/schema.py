"""Schema and validation primitives for the Policy Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from policy_engine.errors import PolicyValidationError


ID_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_\-]{0,63}$"


@dataclass(frozen=True)
class FieldSpec:
    """Field specification for typed validation."""

    name: str
    type: tuple[type, ...] | type
    required: bool = False
    allowed_values: set[Any] | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


class TypedSchema:
    """Generic typed schema validator."""

    def __init__(self, name: str, version: int, fields: dict[str, FieldSpec], allow_unknown: bool = False):
        self.name = name
        self.version = version
        self.fields = fields
        self.allow_unknown = allow_unknown

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise PolicyValidationError(f"{self.name} must be a dictionary")

        errors: list[str] = []
        result = dict(data)

        for key in list(data.keys()):
            if key not in self.fields:
                if not self.allow_unknown:
                    errors.append(f"Unknown field: {key}")
                continue

            spec = self.fields[key]
            value = data[key]
            if value is None and not spec.required:
                continue
            expected = spec.type if isinstance(spec.type, tuple) else (spec.type,)
            if not isinstance(value, expected):
                errors.append(f"{key}: expected {self._type_names(expected)}, got {type(value).__name__}")
                continue
            if spec.allowed_values is not None and value not in spec.allowed_values:
                errors.append(f"{key}: value {value!r} not in allowed set")
            if isinstance(value, str):
                if spec.min_length is not None and len(value) < spec.min_length:
                    errors.append(f"{key}: value too short")
                if spec.max_length is not None and len(value) > spec.max_length:
                    errors.append(f"{key}: value too long")
                # pattern validated externally by caller if needed

        for key, spec in self.fields.items():
            if spec.required and key not in data:
                errors.append(f"{key}: required field missing")

        if errors:
            raise PolicyValidationError(f"{self.name} validation failed: {'; '.join(errors)}")

        result["_schema_version"] = self.version
        return result

    @staticmethod
    def _type_names(types: tuple[type, ...]) -> str:
        return " | ".join(t.__name__ for t in types)


def validate_id(value: str, context: str = "id") -> str:
    """Validate a safe identifier."""
    if not isinstance(value, str):
        raise PolicyValidationError(f"{context} must be a string")
    if not value:
        raise PolicyValidationError(f"{context} must not be empty")
    if len(value) > 64:
        raise PolicyValidationError(f"{context} too long")
    if not value[0].isalpha():
        raise PolicyValidationError(f"{context} must start with a letter")
    if not all(c.isalnum() or c in "_-" for c in value):
        raise PolicyValidationError(f"{context} contains invalid characters")
    return value


def check_bounded_size(value: Any, max_size: int = 1000, max_depth: int = 8, depth: int = 0, max_leaf_len: int = 4096) -> None:
    """Reject oversized or excessively nested values."""
    if depth > max_depth:
        raise PolicyValidationError(f"Value exceeds maximum nesting depth {max_depth}")
    if isinstance(value, str) and len(value) > max_leaf_len:
        raise PolicyValidationError(f"String value exceeds maximum length {max_leaf_len}")
    if isinstance(value, (dict, list)):
        if len(value) > max_size:
            raise PolicyValidationError(f"Container exceeds maximum size {max_size}")
        for v in value.values() if isinstance(value, dict) else value:
            check_bounded_size(v, max_size, max_depth, depth + 1, max_leaf_len)
