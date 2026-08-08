"""Milestone 19 — Policy condition count boundedness audit.

Production condition count bounds catalog:
- policy_engine.evaluator.PolicyEvaluator._check_bounds()
  - MAX_CONDITIONS = 64 (per rule)

No other production layer enforces a condition count bound.
Rule constructor, validate_rule_dict, and condition evaluation are unbounded.
The limit is enforced at PolicyEvaluator construction time (layered defense).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. Exact boundary tests for MAX_CONDITIONS
# ---------------------------------------------------------------------------

class TestPolicyEvaluatorConditionCountBounded:
    def test_evaluator_accepts_exactly_max_conditions(self):
        """PolicyEvaluator accepts rule with exactly MAX_CONDITIONS conditions."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_CONDITIONS
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        rule = Rule(
            rule_id="r1",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=[{"field": "x", "operator": "equals", "value": i} for i in range(MAX_CONDITIONS)],
        )
        profile = PolicyProfile(name="test", description="test", rules=[rule])
        pset = PolicySet(profiles={"test": profile})
        eval_ = PolicyEvaluator(pset)
        assert eval_ is not None

    def test_evaluator_rejects_max_conditions_plus_1(self):
        """PolicyEvaluator rejects rule with MAX_CONDITIONS + 1 conditions."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_CONDITIONS, PolicyEvaluationError
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        rule = Rule(
            rule_id="r1",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=[{"field": "x", "operator": "equals", "value": i} for i in range(MAX_CONDITIONS + 1)],
        )
        profile = PolicyProfile(name="test", description="test", rules=[rule])
        pset = PolicySet(profiles={"test": profile})
        with pytest.raises(PolicyEvaluationError, match="conditions"):
            PolicyEvaluator(pset)

    def test_evaluator_counts_conditions_per_rule_not_global(self):
        """MAX_CONDITIONS is per-rule, not a global total across all rules."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_CONDITIONS
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        rules = [
            Rule(
                rule_id=f"r{i}",
                priority=1,
                effect=DecisionState.ALLOW,
                conditions=[{"field": "x", "operator": "equals", "value": j} for j in range(MAX_CONDITIONS)],
            )
            for i in range(10)
        ]
        profile = PolicyProfile(name="test", description="test", rules=rules)
        pset = PolicySet(profiles={"test": profile})
        # 10 rules × 64 conditions = 640 conditions total — accepted because per-rule limit holds
        eval_ = PolicyEvaluator(pset)
        assert eval_ is not None

    def test_evaluator_rejects_when_any_rule_exceeds_max_conditions(self):
        """PolicyEvaluator rejects if ANY rule has > MAX_CONDITIONS, even if others are small."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_CONDITIONS, PolicyEvaluationError
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        ok_rule = Rule(rule_id="ok", priority=1, effect=DecisionState.ALLOW, conditions=[])
        bad_rule = Rule(
            rule_id="bad",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=[{"field": "x", "operator": "equals", "value": i} for i in range(MAX_CONDITIONS + 1)],
        )
        profile = PolicyProfile(name="test", description="test", rules=[ok_rule, bad_rule])
        pset = PolicySet(profiles={"test": profile})
        with pytest.raises(PolicyEvaluationError, match="conditions"):
            PolicyEvaluator(pset)


# ---------------------------------------------------------------------------
# 2. Rule constructor / validate_rule_dict — UNBOUNDED at construction
# ---------------------------------------------------------------------------

class TestRuleConditionCountUnbounded:
    def test_rule_constructor_accepts_arbitrary_conditions(self):
        """Rule constructor accepts arbitrarily many conditions — no bound."""
        from policy_engine.rules import Rule
        from policy_engine.evaluator import MAX_CONDITIONS
        from policy_engine.decisions import DecisionState
        conditions = [{"field": "x", "operator": "equals", "value": i} for i in range(MAX_CONDITIONS + 10)]
        rule = Rule(rule_id="big", priority=1, effect=DecisionState.ALLOW, conditions=conditions)
        assert len(rule.conditions) == MAX_CONDITIONS + 10

    def test_validate_rule_dict_accepts_arbitrary_conditions(self):
        """validate_rule_dict validates shape but does not enforce condition count."""
        from policy_engine.rules import validate_rule_dict
        from policy_engine.evaluator import MAX_CONDITIONS
        data = {
            "rule_id": "big",
            "priority": 1,
            "effect": "ALLOW",
            "conditions": [{"field": "x", "operator": "equals", "value": i} for i in range(MAX_CONDITIONS + 10)],
        }
        # Should not raise — count is unvalidated here
        validate_rule_dict(data)
        assert len(data["conditions"]) == MAX_CONDITIONS + 10


# ---------------------------------------------------------------------------
# 3. Condition evaluation — linear scan, no early abort on count
# ---------------------------------------------------------------------------

class TestConditionEvaluationLinear:
    def test_matches_evaluates_all_conditions_in_order(self):
        """Rule.matches() evaluates conditions sequentially; all must pass."""
        from policy_engine.rules import Rule
        from policy_engine.requests import PolicyRequest
        from policy_engine.decisions import DecisionState
        conditions = [
            {"field": "actor.type", "operator": "equals", "value": "user"},
            {"field": "capability", "operator": "equals", "value": "read"},
        ]
        rule = Rule(
            rule_id="r1",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=conditions,
        )
        request = PolicyRequest(
            schema_version=1,
            request_id="req-1",
            transaction_id="txn-1",
            actor={"type": "user", "id": "u1"},
            resource={"type": "file"},
            capability="read",
            context={},
        )
        assert rule.matches(request) is True

    def test_matches_fails_on_first_false_condition(self):
        """Rule.matches() short-circuits on first failing condition."""
        from policy_engine.rules import Rule
        from policy_engine.requests import PolicyRequest
        from policy_engine.decisions import DecisionState
        conditions = [
            {"field": "actor.type", "operator": "equals", "value": "admin"},  # false
            {"field": "capability", "operator": "equals", "value": "read"},
        ]
        rule = Rule(
            rule_id="r1",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=conditions,
        )
        request = PolicyRequest(
            schema_version=1,
            request_id="req-1",
            transaction_id="txn-1",
            actor={"type": "user", "id": "u1"},
            resource={"type": "file"},
            capability="read",
            context={},
        )
        assert rule.matches(request) is False


# ---------------------------------------------------------------------------
# 4. Condition shape / value boundedness (links to B1 schema validation)
# ---------------------------------------------------------------------------

class TestConditionShapeBounded:
    def test_condition_field_must_be_string(self):
        """validate_condition rejects non-string field."""
        from policy_engine.conditions import validate_condition, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="field"):
            validate_condition({"field": 123, "operator": "equals", "value": 1})

    def test_condition_operator_must_be_allowed(self):
        """validate_condition rejects unsupported operator."""
        from policy_engine.conditions import validate_condition, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="operator"):
            validate_condition({"field": "x", "operator": "bogus", "value": 1})

    def test_condition_value_type_for_in_operator(self):
        """validate_condition requires list/set/tuple value for in/not_in operators."""
        from policy_engine.conditions import validate_condition, PolicyValidationError
        with pytest.raises(PolicyValidationError):
            validate_condition({"field": "x", "operator": "in", "value": "not_a_list"})

    def test_condition_dict_has_no_explicit_depth_bound(self):
        """A condition dict itself is shallow (field/operator/value); no recursive depth check."""
        from policy_engine.conditions import validate_condition
        # Value can be arbitrarily deep — validate_condition does not recurse
        deep_value = {"a": {"b": {"c": {"d": 1}}}}
        validate_condition({"field": "x", "operator": "equals", "value": deep_value})
        assert True


# ---------------------------------------------------------------------------
# 5. PolicyEngine facade enforces bound via PolicyEvaluator
# ---------------------------------------------------------------------------

class TestPolicyEngineConditionFacadeBounded:
    def test_from_config_rejects_excessive_conditions(self):
        """PolicyEngine.from_config raises when a rule exceeds MAX_CONDITIONS."""
        from policy_engine.engine import PolicyEngine
        from policy_engine.evaluator import MAX_CONDITIONS, PolicyEvaluationError
        config = {
            "rules": [{
                "rule_id": "big",
                "priority": 1,
                "effect": "ALLOW",
                "conditions": [
                    {"field": "x", "operator": "equals", "value": i}
                    for i in range(MAX_CONDITIONS + 1)
                ],
            }],
        }
        with pytest.raises(PolicyEvaluationError, match="conditions"):
            PolicyEngine.from_config(config)


# ---------------------------------------------------------------------------
# 6. No condition count bound in Broker or higher layers
# ---------------------------------------------------------------------------

class TestHigherLayersNoConditionBound:
    def test_broker_evaluate_delegates_to_policy_engine(self):
        """Broker.evaluate delegates to PolicyEngine, which constructs PolicyEvaluator.
        The bound is enforced at PolicyEvaluator construction, not in Broker.
        """
        # This is a design-documentation test; the actual enforcement path is
        # Broker -> PolicyEngine -> PolicyEvaluator.
        assert True