"""Built-in policy profiles and profile model."""

from __future__ import annotations

from policy_engine.actors import actor_may_mutate
from policy_engine.capabilities import READ_ONLY_CAPABILITIES, SHELL_CAPABILITIES, is_mutating_set, is_read_only
from policy_engine.decisions import DecisionState, Requirement
from policy_engine.rules import PolicyProfile, Rule


HIGH_RISK_MUTATIONS = {
    "service.start",
    "service.stop",
    "service.restart",
    "service.reset",
    "vault.unlock",
    "vault.set",
    "vault.get",
    "vault.remove",
    "vault.rotate",
    "update.apply",
    "update.rollback",
    "recovery.restore",
    "recovery.rollback",
    "config.commit",
    "config.rollback",
}


def default_rule_set() -> list[Rule]:
    """Return the authoritative built-in default-deny rule set with profile-specific behavior."""
    rules: list[Rule] = []

    # 1. Invalid / dangerous capabilities are globally denied.
    rules.append(Rule(
        rule_id="global-deny-shell",
        priority=10000,
        effect=DecisionState.DENY,
        capabilities=list(SHELL_CAPABILITIES),
        reason_code="CAPABILITY_NOT_PERMITTED",
    ))

    # 2. Plugin and automation mutation is disabled in Milestone 15.
    rules.append(Rule(
        rule_id="milestone15-deny-plugin-mutation",
        priority=9900,
        effect=DecisionState.DENY,
        actors=["future_plugin", "automation"],
        capabilities=list(is_mutating_set()),
        reason_code="UNKNOWN_ACTOR",
    ))

    # 3. Vault secret retrieval is denied through the broker in Milestone 15.
    rules.append(Rule(
        rule_id="milestone15-deny-vault-get",
        priority=9800,
        effect=DecisionState.DENY,
        capabilities=["vault.get"],
        reason_code="CAPABILITY_NOT_PERMITTED",
    ))

    # 4. Recovery mode active denies normal mutations.
    rules.append(Rule(
        rule_id="recovery-mode-deny-mutations",
        priority=9700,
        effect=DecisionState.DENY,
        capabilities=list(HIGH_RISK_MUTATIONS),
        conditions=[{"field": "context.recovery_mode", "operator": "equals", "value": True}],
        reason_code="RECOVERY_MODE_ACTIVE",
    ))

    # 5. Physical validation required for high-risk resources when not verified.
    rules.append(Rule(
        rule_id="physical-validation-required",
        priority=9600,
        effect=DecisionState.DEFER,
        capabilities=list(HIGH_RISK_MUTATIONS),
        conditions=[{"field": "context.physical_validation_status", "operator": "not_equals", "value": "VERIFIED"}],
        requirements=[Requirement("physical_validation")],
        reason_code="PHYSICAL_VALIDATION_REQUIRED",
    ))

    # 6. High-risk mutations require confirmation for operator.
    rules.append(Rule(
        rule_id="high-risk-mutation-confirm-operator",
        priority=5000,
        effect=DecisionState.CONFIRM,
        actors=["operator"],
        capabilities=list(HIGH_RISK_MUTATIONS),
        requirements=[Requirement("operator_confirmation", scope="single-use", expires_seconds=120)],
        reason_code="MUTATION_REQUIRES_OPERATOR_CONFIRMATION",
    ))

    # 7. Maintenance profile allows maintenance actions with confirmation.
    rules.append(Rule(
        rule_id="maintenance-allowed-with-confirm",
        priority=4000,
        effect=DecisionState.CONFIRM,
        actors=["operator", "service_supervisor"],
        capabilities=["service.start", "service.stop", "service.restart", "service.reset"],
        conditions=[{"field": "context.configuration_profile", "operator": "equals", "value": "maintenance"}],
        requirements=[Requirement("operator_confirmation", scope="single-use", expires_seconds=120)],
        reason_code="MUTATION_REQUIRES_OPERATOR_CONFIRMATION",
    ))

    # 8. Read-only capabilities allow for observer and operator.
    rules.append(Rule(
        rule_id="read-only-allow",
        priority=1000,
        effect=DecisionState.ALLOW,
        actors=["operator", "operations_center", "broker", "installer", "service_supervisor", "update_engine", "recovery_engine"],
        capabilities=list(READ_ONLY_CAPABILITIES),
        reason_code="CAPABILITY_ALLOWED",
    ))

    # 9. Default deny rule with explicit message.
    rules.append(Rule(
        rule_id="default-deny",
        priority=0,
        effect=DecisionState.NOT_APPLICABLE,
        reason_code="DEFAULT_DENY",
    ))

    return rules


def built_in_profiles() -> dict[str, PolicyProfile]:
    base = default_rule_set()
    return {
        "observer": PolicyProfile(
            name="observer",
            description="Read-only access; mutations denied",
            rules=[r for r in base if r.effect != DecisionState.CONFIRM] + [
                Rule(
                    rule_id="observer-deny-mutation",
                    priority=6000,
                    effect=DecisionState.DENY,
                    capabilities=list(is_mutating_set()),
                    reason_code="PROFILE_RESTRICTED",
                ),
            ],
        ),
        "operator": PolicyProfile(
            name="operator",
            description="Read plus selected mutations requiring confirmation",
            rules=base,
        ),
        "administrator": PolicyProfile(
            name="administrator",
            description="Broader access with bounded confirmation requirements; not unrestricted",
            rules=base,
        ),
        "maintenance": PolicyProfile(
            name="maintenance",
            description="Maintenance actions on services and verified updates",
            rules=base,
        ),
        "recovery": PolicyProfile(
            name="recovery",
            description="Recovery actions with strict bundle verification",
            rules=base + [
                Rule(
                    rule_id="recovery-actions-require-mode",
                    priority=9500,
                    effect=DecisionState.CONFIRM,
                    actors=["operator"],
                    capabilities=["recovery.restore", "recovery.rollback"],
                    conditions=[{"field": "context.recovery_mode", "operator": "equals", "value": True}],
                    requirements=[
                        Requirement("operator_confirmation", scope="single-use", expires_seconds=120),
                        Requirement("rollback_available"),
                    ],
                    reason_code="RECOVERY_MODE_ACTIVE",
                ),
            ],
        ),
        "development": PolicyProfile(
            name="development",
            description="Development-only capabilities; must not be selected silently in production",
            rules=base,
        ),
    }


# Forward import to avoid circular references at module load time
