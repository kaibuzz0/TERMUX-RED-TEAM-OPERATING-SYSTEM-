"""Policy loading through config_engine and built-in defaults."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from policy_engine.errors import PolicyNotFoundError, PolicyValidationError
from policy_engine.rules import PolicyProfile, PolicySet, Rule
from policy_engine.profiles import built_in_profiles
from policy_engine.rules import validate_rule_dict


class PolicyLoader:
    """Load policy configuration from authoritative sources.

    Sources:
    1. Built-in default-deny rules
    2. Selected policy profile from config_engine
    3. Runtime emergency restrictions (additive deny)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def load(self, profile_name: str | None = None, emergency: dict[str, Any] | None = None) -> PolicySet:
        """Load and merge policy sources."""
        profiles = built_in_profiles()

        active_profile = profile_name or self.config.get("default_profile", "observer")
        if active_profile not in profiles:
            raise PolicyValidationError(f"Unknown policy profile: {active_profile!r}")

        # Optionally load additional rules from config (narrowly scoped)
        configured_rules = self.config.get("rules", [])
        if configured_rules:
            if not isinstance(configured_rules, list):
                raise PolicyValidationError("Configured rules must be a list")
            extra: list[Rule] = []
            for raw in configured_rules:
                validate_rule_dict(raw)
                extra.append(Rule.from_dict(raw))
            profiles[active_profile].rules.extend(extra)

        # Apply emergency restrictions: prepend deny-all mutations if requested.
        if emergency:
            rules = _emergency_rules(emergency)
            # Emergency rules are added to every profile and highest priority.
            for prof in profiles.values():
                prof.rules = rules + prof.rules

        return PolicySet(profiles)


def _emergency_rules(emergency: dict[str, Any]) -> list[Rule]:
    """Generate emergency restriction rules that only reduce authority."""
    from policy_engine.capabilities import is_mutating_set
    from policy_engine.decisions import DecisionState

    rules: list[Rule] = []
    if emergency.get("deny_all_mutations"):
        rules.append(Rule(
            rule_id="emergency-deny-all-mutations",
            priority=11000,
            effect=DecisionState.DENY,
            capabilities=list(is_mutating_set()),
            reason_code="RECOVERY_MODE_ACTIVE",
        ))
    if emergency.get("observer_only"):
        rules.append(Rule(
            rule_id="emergency-observer-only",
            priority=11000,
            effect=DecisionState.DENY,
            capabilities=list(is_mutating_set()),
            reason_code="PROFILE_RESTRICTED",
        ))
    if emergency.get("recovery_only"):
        from policy_engine.capabilities import CAPABILITIES
        rules.append(Rule(
            rule_id="emergency-recovery-only",
            priority=10900,
            effect=DecisionState.DENY,
            capabilities=[c for c in CAPABILITIES if not c.startswith("recovery.")],
            reason_code="RECOVERY_MODE_ACTIVE",
        ))
    return rules


def load_from_config_engine(repo_root: Path | None = None, profile: str | None = None) -> PolicySet:
    """Load policy configuration through the Configuration Engine."""
    from config_engine.config import get_config
    cfg = get_config("policy", repo_root=repo_root, profile=profile)
    loader = PolicyLoader(cfg)
    return loader.load(cfg.get("active_profile"), cfg.get("emergency"))
