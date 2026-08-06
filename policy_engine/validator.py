"""Policy validation orchestrator."""

from __future__ import annotations

from typing import Any

from policy_engine.errors import PolicyValidationError
from policy_engine.loader import PolicyLoader
from policy_engine.profiles import built_in_profiles


class PolicyValidator:
    """Validate policy configuration and rule sets without mutating state."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def validate(self) -> list[str]:
        """Return a list of warnings; raise on critical errors."""
        warnings: list[str] = []

        active = self.config.get("active_profile", "observer")
        known = set(built_in_profiles().keys())
        if active not in known:
            raise PolicyValidationError(f"Active profile {active!r} is not a built-in profile")

        if self.config.get("emergency"):
            emergency = self.config["emergency"]
            if not isinstance(emergency, dict):
                raise PolicyValidationError("emergency must be a dictionary")
            for key in emergency:
                if key not in {"deny_all_mutations", "observer_only", "recovery_only"}:
                    raise PolicyValidationError(f"Unknown emergency restriction: {key!r}")

        # Attempt load to surface rule validation errors
        loader = PolicyLoader(self.config)
        try:
            loader.load(active)
        except PolicyValidationError as e:
            raise

        return warnings


def validate_policy_config(config: dict[str, Any]) -> list[str]:
    """Top-level validation convenience."""
    return PolicyValidator(config).validate()
