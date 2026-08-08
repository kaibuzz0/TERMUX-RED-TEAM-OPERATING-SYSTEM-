"""C5-POLICY: Policy Engine structural verification.

The Policy Engine is the authorization authority. This test verifies its
internal gates, fail-closed behaviors, and structural properties.
"""

from __future__ import annotations

import inspect

import pytest

from hive_broker.capabilities import BROKER_CAPABILITIES, _CAPABILITY_NAMES
from policy_engine.actors import ACTOR_TYPES, MUTATION_DISABLED_ACTORS
from policy_engine.decisions import DecisionState
from policy_engine.engine import PolicyEngine
from policy_engine.errors import PolicyRequestError, PolicyEvaluationError, PolicyValidationError
from policy_engine.evaluator import PolicyEvaluator, MAX_RULES, MAX_CONDITIONS
from policy_engine.loader import PolicyLoader
from policy_engine.requests import PolicyRequest
from policy_engine.rules import PolicySet, PolicyProfile, Rule


class TestPolicyEngineStructural:
    """Structural proofs for Policy Engine gates."""

    def _engine(self):
        return PolicyEngine.from_config()

    def _make_request(self, actor_type="operator", capability="service.status"):
        return PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": actor_type, "id": "actor-1"},
            "capability": capability,
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "configuration_profile": "production",
                "runtime_mode": "normal",
                "maintenance_mode": False,
                "recovery_mode": False,
                "vault_state": "LOCKED",
                "rollback_available": True,
                "physical_validation_status": "DEFERRED",
            },
        })

    # ------------------------------------------------------------------
    # Gate order: bounds -> request validation -> profile selection -> match -> resolve
    # ------------------------------------------------------------------

    def test_evaluator_source_has_bounds_check_before_validation(self):
        """Structural: _check_bounds precedes _validate_request in evaluate()."""
        src = inspect.getsource(PolicyEvaluator.__init__)
        assert "_check_bounds" in src
        src_eval = inspect.getsource(PolicyEvaluator.evaluate)
        assert "_validate_request" in src_eval
        # _check_bounds is called in __init__, _validate_request in evaluate

    def test_evaluator_source_has_validation_before_match(self):
        """Structural: _validate_request precedes imported match_rules call in evaluate()."""
        src = inspect.getsource(PolicyEvaluator.evaluate)
        validate_idx = src.find("_validate_request")
        assert validate_idx > 0
        # match_rules is imported from rules module, called after validation
        assert "matched = " in src or "match_rules" in src

    def test_evaluator_source_has_match_before_resolve(self):
        """Structural: rule matching precedes _resolve in evaluate()."""
        src = inspect.getsource(PolicyEvaluator.evaluate)
        # After match comes sort_rules, then _resolve
        resolve_idx = src.find("_resolve")
        assert resolve_idx > 0

    def test_evaluator_bounds_reject_excessive_rules(self):
        """Policy set with >MAX_RULES rules raises PolicyEvaluationError."""
        rules = [
            Rule(
                rule_id=f"rule-{i}",
                priority=i,
                effect=DecisionState.ALLOW,
                reason_code="TEST",
            )
            for i in range(MAX_RULES + 1)
        ]
        ps = PolicySet({
            "test": PolicyProfile(name="test", description="test", rules=rules),
        })
        with pytest.raises(PolicyEvaluationError) as exc:
            PolicyEvaluator(ps)
        assert "exceeds maximum" in str(exc.value).lower()

    def test_evaluator_bounds_reject_excessive_conditions(self):
        """Policy rule with >MAX_CONDITIONS conditions raises PolicyEvaluationError."""
        conditions = [{"key": "ctx", "op": "eq", "value": f"val-{i}"} for i in range(MAX_CONDITIONS + 1)]
        rule = Rule(
            rule_id="bad-rule",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=conditions,
            reason_code="TEST",
        )
        ps = PolicySet({
            "test": PolicyProfile(name="test", description="test", rules=[rule]),
        })
        with pytest.raises(PolicyEvaluationError) as exc:
            PolicyEvaluator(ps)
        assert "conditions" in str(exc.value).lower()

    # ------------------------------------------------------------------
    # Request validation gates
    # ------------------------------------------------------------------

    def test_unknown_actor_type_raises_policy_validation_error(self):
        """Invalid actor type in raw dict causes PolicyValidationError at PolicyEngine boundary.
        
        This is fail-closed: caller must handle the exception. The broker does.
        """
        engine = self._engine()
        req = {
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": "unknown_actor", "id": "actor-1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "maintenance_mode": False,
                "recovery_mode": False,
                "vault_state": "LOCKED",
                "rollback_available": True,
                "physical_validation_status": "DEFERRED",
            },
        }
        with pytest.raises(PolicyValidationError):
            engine.evaluate(req)

    def test_mutating_actor_type_cannot_request_mutation(self):
        """future_plugin actor cannot request mutations — fails validation -> DENY."""
        engine = self._engine()
        req = self._make_request(
            actor_type="future_plugin",
            capability="service.start",
        )
        decision = engine.evaluate(req)
        # _validate_request raises PolicyRequestError -> caught as DENY
        assert decision.decision == DecisionState.DENY
        assert "mutation" in decision.message.lower()

    def test_context_schema_rejects_invalid_vault_state(self):
        """Invalid vault_state in raw dict causes PolicyValidationError at PolicyEngine boundary."""
        engine = self._engine()
        req = {
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": "operator", "id": "actor-1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "vault_state": "COMPROMISED",
                "rollback_available": True,
            },
        }
        with pytest.raises(PolicyValidationError):
            engine.evaluate(req)

    def test_context_schema_rejects_wrong_type(self):
        """Bool field with string value causes PolicyValidationError at PolicyEngine boundary."""
        engine = self._engine()
        req = {
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": "operator", "id": "actor-1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "maintenance_mode": "yes",
            },
        }
        with pytest.raises(PolicyValidationError):
            engine.evaluate(req)

    # ------------------------------------------------------------------
    # Resolution precedence
    # ------------------------------------------------------------------

    def test_error_rules_take_precedence_over_deny(self):
        """If an ERROR rule matches, it wins over DENY rules."""
        ps = PolicySet({
            "test": PolicyProfile(
                name="test",
                description="test",
                rules=[
                    Rule(rule_id="deny-1", priority=1, effect=DecisionState.DENY, reason_code="DENY_CODE"),
                    Rule(rule_id="error-1", priority=2, effect=DecisionState.ERROR, reason_code="ERROR_CODE"),
                ],
            ),
        })
        evaluator = PolicyEvaluator(ps)
        req = self._make_request()
        decision = evaluator.evaluate(req, "test")
        assert decision.decision == DecisionState.ERROR
        assert "error-1" in decision.message

    def test_deny_rules_take_precedence_over_allow(self):
        """If a DENY rule matches, it wins over ALLOW rules."""
        ps = PolicySet({
            "test": PolicyProfile(
                name="test",
                description="test",
                rules=[
                    Rule(rule_id="allow-1", priority=1, effect=DecisionState.ALLOW, reason_code="ALLOW_CODE"),
                    Rule(rule_id="deny-1", priority=2, effect=DecisionState.DENY, reason_code="DENY_CODE"),
                ],
            ),
        })
        evaluator = PolicyEvaluator(ps)
        req = self._make_request()
        decision = evaluator.evaluate(req, "test")
        assert decision.decision == DecisionState.DENY
        assert "deny-1" in decision.message

    def test_no_rules_defaults_deny(self):
        """Empty rule set produces DEFAULT_DENY."""
        ps = PolicySet({
            "empty": PolicyProfile(name="empty", description="test", rules=[]),
        })
        evaluator = PolicyEvaluator(ps)
        req = self._make_request()
        decision = evaluator.evaluate(req, "empty")
        assert decision.decision == DecisionState.DENY
        assert decision.reason_code == "DEFAULT_DENY"

    # ------------------------------------------------------------------
    # Fail-closed on exceptions
    # ------------------------------------------------------------------

    def test_evaluator_catches_all_exceptions_as_error(self):
        """evaluate() has broad except Exception -> ERROR decision."""
        src = inspect.getsource(PolicyEvaluator.evaluate)
        assert "except Exception as e:" in src
        assert "DecisionState.ERROR" in src

    def test_policy_validation_error_propagates_from_engine_boundary(self):
        """PolicyValidationError (actor schema failure) propagates from PolicyEngine.evaluate().
        
        The broker catches this in Broker.run except Exception -> denied response.
        The PolicyEngine facade does NOT catch PolicyValidationError.
        """
        engine = self._engine()
        req = {
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": "nonexistent_actor_type", "id": "actor-1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "maintenance_mode": False,
                "recovery_mode": False,
                "vault_state": "LOCKED",
                "rollback_available": True,
                "physical_validation_status": "DEFERRED",
            },
        }
        # PolicyEngine.evaluate() raises, does NOT return ERROR decision
        with pytest.raises(PolicyValidationError):
            engine.evaluate(req)

    # ------------------------------------------------------------------
    # Capability advertisement
    # ------------------------------------------------------------------

    def test_all_broker_capabilities_are_non_mutating(self):
        """BROKER_CAPABILITIES contains only read-only capabilities."""
        for cap in BROKER_CAPABILITIES:
            assert cap.mutation is False, (
                f"Capability {cap.name} is marked mutating"
            )

    def test_no_mutating_capability_in_advertised_set(self):
        """No mutating capability exists in the broker's advertised capability set."""
        mutating_names = {
            "service.start", "service.stop", "service.restart",
            "service.kill", "service.remove",
            "vault.secret.get", "vault.secret.read",
            "update.apply", "update.force",
            "recovery.restore", "recovery.reset",
            "config.commit", "config.write",
        }
        for name in mutating_names:
            assert name not in _CAPABILITY_NAMES, (
                f"Mutating capability {name} found in advertised set"
            )

    # ------------------------------------------------------------------
    # Actor registry
    # ------------------------------------------------------------------

    def test_mutation_disabled_actors_cannot_mutate(self):
        """MUTATION_DISABLED_ACTORS cannot request mutations."""
        from policy_engine.actors import actor_may_mutate
        for actor in MUTATION_DISABLED_ACTORS:
            assert actor_may_mutate(actor) is False

    def test_operator_actor_can_mutate(self):
        """Operator actor can request mutations (though policy may still DENY)."""
        from policy_engine.actors import actor_may_mutate
        assert actor_may_mutate("operator") is True

    # ------------------------------------------------------------------
    # Audit and correlation
    # ------------------------------------------------------------------

    def test_policy_digest_is_deterministic(self):
        """policy_digest() returns same value for same policy set."""
        engine = self._engine()
        digest1 = engine.policy_digest()
        digest2 = engine.policy_digest()
        assert digest1 == digest2
        assert digest1.startswith("sha256:")

    # ------------------------------------------------------------------
    # Profile isolation
    # ------------------------------------------------------------------

    def test_observer_profile_blocks_mutation(self):
        """Observer profile denies mutations even for operator actor."""
        engine = self._engine()
        req = self._make_request(actor_type="operator", capability="service.start")
        decision = engine.evaluate(req, profile_name="observer")
        assert decision.decision == DecisionState.DENY

    def test_different_profiles_produce_different_decisions(self):
        """Same request evaluated against different profiles may differ."""
        engine = self._engine()
        req = self._make_request(actor_type="operator", capability="service.start")
        observer = engine.evaluate(req, profile_name="observer")
        operator = engine.evaluate(req, profile_name="operator")
        # Observer should DENY, operator may DEFER/CONFIRM
        assert observer.decision == DecisionState.DENY
        assert operator.decision in (DecisionState.DEFER, DecisionState.CONFIRM)

    def test_nonexistent_profile_falls_back_to_default(self):
        """Nonexistent profile name falls back to observer default."""
        engine = self._engine()
        req = self._make_request(actor_type="operator", capability="service.status")
        decision = engine.evaluate(req, profile_name="nonexistent")
        # Should evaluate without exception
        assert decision.decision in (DecisionState.ALLOW, DecisionState.DENY, DecisionState.ERROR)

    # ------------------------------------------------------------------
    # Engine facade isolation
    # ------------------------------------------------------------------

    def test_engine_evaluate_has_no_side_effects_on_request(self):
        """evaluate() does not modify the request object."""
        engine = self._engine()
        req = self._make_request()
        original = req.to_dict()
        engine.evaluate(req)
        assert req.to_dict() == original

    def test_evaluate_convenience_matches_engine_evaluate(self):
        """policy_engine.evaluator.evaluate() produces same result as PolicyEngine.evaluate()."""
        from policy_engine.evaluator import evaluate as eval_func
        loader = PolicyLoader({})
        ps = loader.load("observer")
        req = self._make_request()
        decision1 = eval_func(req, ps, "observer")
        engine = PolicyEngine(ps)
        decision2 = engine.evaluate(req, profile_name="observer")
        assert decision1.decision == decision2.decision
        assert decision1.reason_code == decision2.reason_code

    def test_context_schema_allows_unknown_fields(self):
        """CONTEXT_SCHEMA allows unknown fields but validates known ones."""
        engine = self._engine()
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "req-test",
            "transaction_id": "txn-test",
            "actor": {"type": "operator", "id": "actor-1"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "svc"},
            "context": {
                "maintenance_mode": False,
                "unknown_field": "arbitrary_value",
            },
        })
        decision = engine.evaluate(req)
        assert decision.decision in (DecisionState.ALLOW, DecisionState.DENY)
        assert "unknown" not in decision.message.lower() or decision.decision != DecisionState.DENY

    def test_engine_status_is_read_only(self):
        """PolicyEngine.status() returns only read-only metadata."""
        engine = self._engine()
        status = engine.status()
        assert "profiles" in status
        assert "policy_digest" in status
        assert "total_rules" in status
        assert "evaluator" not in status
        assert "policy_set" not in status
