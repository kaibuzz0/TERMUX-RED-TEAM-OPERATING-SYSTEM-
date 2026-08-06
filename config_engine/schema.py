"""Typed configuration schemas and validation for all Hive subsystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from config_engine.errors import ConfigValidationError


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single configuration field."""

    name: str
    type: tuple[type, ...] | type
    required: bool = False
    default: Any = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    allowed_values: set[Any] | None = None
    allow_empty: bool = True
    nested_schema: "ConfigSchema | None" = None
    deprecated: bool = False
    removed: bool = False
    extensible: bool = False


@dataclass
class ConfigSchema:
    """Schema definition for a subsystem configuration."""

    name: str
    version: int = 1
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    extensible: bool = False
    allow_unknown: bool = False

    @staticmethod
    def _check_size(value: Any, max_size: int = 1000) -> None:
        """Reject oversized containers."""
        if isinstance(value, (dict, list)) and len(value) > max_size:
            raise ConfigValidationError(f"Container exceeds maximum size {max_size}")

    @staticmethod
    def _check_depth(value: Any, max_depth: int = 10, current: int = 0) -> None:
        """Reject excessively nested containers."""
        if current > max_depth:
            raise ConfigValidationError(f"Configuration exceeds maximum nesting depth {max_depth}")
        if isinstance(value, dict):
            for v in value.values():
                ConfigSchema._check_depth(v, max_depth, current + 1)
        elif isinstance(value, list):
            for v in value:
                ConfigSchema._check_depth(v, max_depth, current + 1)

    def validate(self, data: dict[str, Any], strict: bool = True) -> dict[str, Any]:
        """Validate a raw configuration dictionary and return normalized data."""
        if not isinstance(data, dict):
            raise ConfigValidationError(f"{self.name} configuration must be a dictionary")
        self._check_depth(data)
        self._check_size(data)

        errors: list[dict] = []
        warnings: list[dict] = []
        result: dict[str, Any] = {}

        # Check unknown fields
        for key in data:
            if key in self.fields:
                continue
            if self.allow_unknown or self.extensible:
                result[key] = data[key]
                continue
            errors.append({"field": key, "message": f"Unknown field in {self.name}"})

        # Validate known fields
        for name, spec in self.fields.items():
            if name in data:
                value = data[name]
            elif spec.required:
                if spec.default is not None:
                    value = spec.default
                else:
                    errors.append({"field": name, "message": "Required field missing"})
                    continue
            else:
                if spec.default is not None:
                    result[name] = spec.default
                continue

            if spec.removed:
                errors.append({"field": name, "message": f"Field {name!r} was removed"})
                continue

            if spec.deprecated:
                warnings.append({"field": name, "message": f"Field {name!r} is deprecated"})

            try:
                normalized = self._validate_field(spec, value)
                result[name] = normalized
            except ConfigValidationError as e:
                errors.append({"field": name, "message": str(e)})

        if errors:
            raise ConfigValidationError(
                f"Validation failed for {self.name}",
                details=errors,
            )

        result["_warnings"] = warnings
        result["_schema_version"] = self.version
        return result

    def _validate_field(self, spec: FieldSpec, value: Any) -> Any:
        """Validate a single field value."""
        expected = spec.type
        if not isinstance(expected, tuple):
            expected = (expected,)

        # None handling for optional fields
        if value is None and not spec.required:
            return None

        if not isinstance(value, expected):
            raise ConfigValidationError(
                f"Expected type {self._type_names(expected)}, got {type(value).__name__}"
            )

        if isinstance(value, (int, float)):
            if isinstance(value, float) and not (value == value and value != float("inf") and value != float("-inf")):
                raise ConfigValidationError("Numeric value must be finite")
            if spec.min_value is not None and value < spec.min_value:
                raise ConfigValidationError(f"Value {value} below minimum {spec.min_value}")
            if spec.max_value is not None and value > spec.max_value:
                raise ConfigValidationError(f"Value {value} above maximum {spec.max_value}")

        if isinstance(value, str) and not spec.allow_empty and value == "":
            raise ConfigValidationError("Value must be non-empty")

        if isinstance(value, (list, dict)) and not spec.allow_empty and len(value) == 0:
            raise ConfigValidationError("Value must be non-empty")

        if spec.allowed_values is not None and value not in spec.allowed_values:
            raise ConfigValidationError(
                f"Value {value!r} not in allowed values: {sorted(spec.allowed_values)}"
            )

        if spec.nested_schema is not None and isinstance(value, dict):
            return spec.nested_schema.validate(value, strict=False)

        return value

    @staticmethod
    def _type_names(types: tuple[type, ...]) -> str:
        names = [t.__name__ for t in types]
        return " | ".join(names)


class SchemaRegistry:
    """Registry of subsystem configuration schemas."""

    def __init__(self) -> None:
        self._schemas: dict[str, ConfigSchema] = {}

    def register(self, schema: ConfigSchema) -> None:
        if schema.name in self._schemas:
            raise ConfigValidationError(f"Schema {schema.name!r} already registered")
        self._schemas[schema.name] = schema

    def get(self, name: str) -> ConfigSchema:
        if name not in self._schemas:
            raise ConfigValidationError(f"Unknown subsystem schema: {name}")
        return self._schemas[name]

    def list(self) -> list[str]:
        return sorted(self._schemas.keys())

    def has(self, name: str) -> bool:
        return name in self._schemas
