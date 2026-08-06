"""Declarative condition evaluation."""

from __future__ import annotations

from typing import Any

from policy_engine.errors import PolicyValidationError


ALLOWED_OPERATORS = {
    "equals",
    "not_equals",
    "in",
    "not_in",
    "contains",
    "exists",
    "greater_than",
    "less_than",
}


def get_value_at_path(data: dict[str, Any], path: str) -> tuple[bool, Any]:
    """Resolve a dotted path against a nested dictionary."""
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def evaluate_condition(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    """Evaluate a single declarative condition."""
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")

    if not isinstance(field, str) or not isinstance(operator, str):
        raise PolicyValidationError("Condition must have string field and operator")
    if operator not in ALLOWED_OPERATORS:
        raise PolicyValidationError(f"Unsupported condition operator: {operator!r}")

    exists, actual = get_value_at_path(context, field)

    if operator == "exists":
        return exists
    if not exists:
        return False

    if operator == "equals":
        return actual == value
    if operator == "not_equals":
        return actual != value
    if operator == "in":
        return isinstance(value, (list, set, tuple)) and actual in value
    if operator == "not_in":
        return isinstance(value, (list, set, tuple)) and actual not in value
    if operator == "contains":
        return isinstance(actual, (list, set, tuple, str)) and value in actual
    if operator == "greater_than":
        return isinstance(actual, (int, float)) and isinstance(value, (int, float)) and actual > value
    if operator == "less_than":
        return isinstance(actual, (int, float)) and isinstance(value, (int, float)) and actual < value

    raise PolicyValidationError(f"Could not evaluate condition: {condition}")


def validate_condition(condition: dict[str, Any]) -> None:
    field = condition.get("field")
    operator = condition.get("operator")
    if not isinstance(field, str) or not isinstance(operator, str):
        raise PolicyValidationError("Condition field and operator must be strings")
    if operator not in ALLOWED_OPERATORS:
        raise PolicyValidationError(f"Unsupported operator: {operator!r}")
    if "value" not in condition and operator != "exists":
        raise PolicyValidationError(f"Condition operator {operator!r} requires a value")
    if operator in ("in", "not_in") and not isinstance(condition.get("value"), (list, set, tuple)):
        raise PolicyValidationError(f"Operator {operator!r} requires a list value")
    # Reject dangerous patterns in field path
    if any(c in field for c in " \n\r\t`$()[]{}"):
        raise PolicyValidationError(f"Invalid characters in condition field: {field!r}")
