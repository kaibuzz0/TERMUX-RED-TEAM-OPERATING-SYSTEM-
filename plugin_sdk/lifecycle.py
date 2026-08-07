"""Plugin lifecycle states and transitions.

Default state is DISABLED. No auto-enable on install. No code execution during
validation or install planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from plugin_sdk.errors import PluginLifecycleError

LIFECYCLE_STATES = frozenset({
    "DISCOVERED",
    "VALIDATED",
    "INCOMPATIBLE",
    "DISABLED",
    "ENABLED",
    "DEGRADED",
    "ERROR",
    "QUARANTINED",
    "REMOVED",
})

DEFAULT_STATE = "DISABLED"

VALID_TRANSITIONS: Dict[str, set[str]] = {
    "DISCOVERED": {"VALIDATED", "INCOMPATIBLE", "DISABLED", "REMOVED"},
    "VALIDATED": {"DISABLED", "INCOMPATIBLE", "REMOVED"},
    "INCOMPATIBLE": {"REMOVED", "DISABLED"},
    "DISABLED": {"ENABLED", "REMOVED", "ERROR"},
    "ENABLED": {"DISABLED", "DEGRADED", "ERROR", "QUARANTINED"},
    "DEGRADED": {"DISABLED", "ENABLED", "ERROR", "QUARANTINED"},
    "ERROR": {"DISABLED", "QUARANTINED"},
    "QUARANTINED": {"DISABLED", "REMOVED"},
    "REMOVED": set(),
}


@dataclass
class PluginLifecycle:
    plugin_id: str
    state: str = DEFAULT_STATE
    failure_count: int = 0
    max_failures: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state not in LIFECYCLE_STATES:
            raise PluginLifecycleError(f"invalid lifecycle state: {self.state!r}")

    def transition(self, new_state: str, reason: str = "") -> None:
        if new_state not in LIFECYCLE_STATES:
            raise PluginLifecycleError(f"invalid lifecycle state: {new_state!r}")
        if new_state not in VALID_TRANSITIONS.get(self.state, set()):
            raise PluginLifecycleError(
                f"invalid transition from {self.state} to {new_state}: {reason}"
            )
        self.state = new_state
        if reason:
            self.metadata["last_transition_reason"] = reason

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.transition("QUARANTINED", f"failure count {self.failure_count} exceeded threshold")
        else:
            self.transition("DEGRADED", f"failure {self.failure_count}")
