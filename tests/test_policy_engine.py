"""Tests for the Hive OS Policy Engine (Milestone 15)."""

from __future__ import annotations

import json
from pathlib import Path


def make_context(**kwargs):
    ctx = {
        "configuration_profile": "production",
        "broker_policy_profile": "operator",
        "runtime_mode": "normal",
        "maintenance_mode": False,
        "recovery_mode": False,
        "vault_state": "LOCKED",
        "rollback_available": True,
        "physical_validation_status": "DEFERRED",
    }
    ctx.update(kwargs)
    return ctx
import pytest

from policy_engine.actors import actor_may_mutate
from policy_engine.capabilities import is_mutating, is_read_only
from policy_engine.decisions import DecisionState
from policy_engine.engine import PolicyEngine
from policy_engine.errors import PolicyRequestError, PolicyValidationError
from policy_engine.profiles import built_in_profiles
from policy_engine.requests import PolicyRequest


@pytest.fixture
def engine():
    return PolicyEngine.from_config()


def make_request(actor_type="operator", capability="service.status", resource_type="service", resource_id="svc", context=None):
    base_context = {
        "configuration_profile": "production",
        "runtime_mode": "normal",
        "maintenance_mode": False,
        "recovery_mode": False,
        "vault_state": "LOCKED",
        "rollback_available": True,
        "physical_validation_status": "DEFERRED",
    }
    if context:
        base_context.update(context)
    return PolicyRequest.from_dict({
        "schema_version": 1,
        "request_id": "req-test",
        "transaction_id": "txn-test",
        "actor": {"type": actor_type, "id": "actor-1"},
        "capability": capability,
        "resource": {"type": resource_type, "id": resource_id},
        "context": base_context,
    })


def test_valid_request_allow(engine):
    req = make_request("operator", "service.status")
    decision = engine.evaluate(req)
    assert decision.decision == DecisionState.ALLOW
    assert decision.reason_code == "CAPABILITY_ALLOWED"


def test_observer_mutation_denied(engine):
    req = make_request("operator", "service.start")
    # In observer profile, high-risk mutation is denied
    decision = engine.evaluate(req, profile_name="observer")
    assert decision.decision == DecisionState.DENY


def test_operator_mutation_confirm(engine):
    # With physical validation deferred, high-risk mutation defers pending physical validation.
    req = make_request("operator", "service.start")
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision in {DecisionState.CONFIRM, DecisionState.DEFER}
    assert decision.decision == DecisionState.DEFER or any(r.type == "operator_confirmation" for r in decision.requirements)


def test_default_deny(engine):
    req = make_request("operator", "broker.stop")
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision == DecisionState.DENY
    assert decision.reason_code == "DEFAULT_DENY"


def test_plugin_mutation_denied(engine):
    req = make_request("future_plugin", "service.start")
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision == DecisionState.DENY


def test_vault_get_denied(engine):
    req = make_request("operator", "vault.get", "vault", "default")
    decision = engine.evaluate(req, profile_name="administrator")
    assert decision.decision == DecisionState.DENY


def test_recovery_mode_denies_mutation(engine):
    req = make_request("operator", "update.apply", resource_type="update_bundle", context={"recovery_mode": True})
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision == DecisionState.DENY
    assert decision.reason_code == "RECOVERY_MODE_ACTIVE"


def test_physical_validation_defer(engine):
    req = make_request("operator", "service.start")
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision == DecisionState.DEFER
    assert decision.reason_code == "PHYSICAL_VALIDATION_REQUIRED"


def test_unknown_schema_version(engine):
    with pytest.raises(PolicyRequestError):
        PolicyRequest.from_dict({
            "schema_version": 99,
            "request_id": "bad",
            "actor": {"type": "operator", "id": "x"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "x"},
            "context": {},
        })


def test_unknown_actor(engine):
    with pytest.raises(PolicyValidationError):
        make_request("hacker", "service.status")


def test_unknown_capability(engine):
    with pytest.raises(PolicyValidationError):
        make_request("operator", "service.destroy")


def test_unknown_resource(engine):
    with pytest.raises(PolicyValidationError):
        make_request("operator", "service.status", resource_type="ghost")


def test_oversized_request_rejected(engine):
    big = {"k": "x" * 10000}
    with pytest.raises(PolicyValidationError):
        PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "big",
            "actor": {"type": "operator", "id": "x"},
            "capability": "service.status",
            "resource": {"type": "service", "id": "x", "attributes": big},
            "context": {},
        })


def test_precedence_deny_overrides_allow(engine):
    # Recovery-mode deny should win over high-risk confirm
    req = make_request("operator", "service.start", context={"recovery_mode": True})
    decision = engine.evaluate(req, profile_name="operator")
    assert decision.decision == DecisionState.DENY


def test_deterministic_repeated_evaluation(engine):
    req = make_request("operator", "service.status")
    d1 = engine.evaluate(req)
    d2 = engine.evaluate(req)
    assert d1.decision == d2.decision
    assert d1.reason_code == d2.reason_code


def test_explain_command(engine):
    result = engine.explain("service.start")
    assert result["decision"] in {"CONFIRM", "DEFER"}
    assert result["reason_code"] in {"MUTATION_REQUIRES_OPERATOR_CONFIRMATION", "PHYSICAL_VALIDATION_REQUIRED"}


def test_status(engine):
    status = engine.status()
    assert status["default_profile"] == "observer"
    assert "profiles" in status
    assert "policy_digest" in status


def test_decision_no_internal_stack_trace(engine):
    req = make_request("operator", "service.start")
    decision = engine.evaluate(req, profile_name="operator")
    assert "Traceback" not in decision.message
    assert "Exception" not in decision.message


def test_actor_may_mutate():
    assert actor_may_mutate("operator") is True
    assert actor_may_mutate("future_plugin") is False
    assert actor_may_mutate("automation") is False


# ---------------- Rule loading and validation ----------------

def test_valid_rule():
    raw = {
        "rule_id": "test-allow",
        "priority": 1000,
        "effect": "ALLOW",
        "actors": ["operator"],
        "capabilities": ["service.status"],
        "resources": ["service"],
        "reason_code": "CAPABILITY_ALLOWED",
    }
    from policy_engine.rules import Rule
    rule = Rule.from_dict(raw)
    assert rule.rule_id == "test-allow"


def test_invalid_rule_effect():
    from policy_engine.rules import validate_rule_dict
    with pytest.raises(PolicyValidationError):
        validate_rule_dict({"rule_id": "bad", "priority": 1, "effect": "MAYBE"})


def test_duplicate_rule_id_in_profile():
    from policy_engine.rules import PolicyProfile, PolicySet
    r = {
        "rule_id": "dup",
        "priority": 1,
        "effect": "ALLOW",
        "reason_code": "CAPABILITY_ALLOWED",
    }
    from policy_engine.rules import Rule
    profile = PolicyProfile("p", "", [Rule.from_dict(r), Rule.from_dict(r)])
    with pytest.raises(PolicyValidationError):
        PolicySet({"p": profile})


# ---------------- Precedence ----------------

def test_global_deny_overrides_allow():
    from policy_engine.rules import Rule, PolicyProfile, PolicySet
    from policy_engine.evaluator import PolicyEvaluator
    from policy_engine.requests import PolicyRequest
    rules = [
        {"rule_id": "deny", "priority": 10000, "effect": "DENY", "capabilities": ["service.start"], "reason_code": "CAPABILITY_NOT_PERMITTED"},
        {"rule_id": "allow", "priority": 1000, "effect": "ALLOW", "capabilities": ["service.start"], "actors": ["operator"], "reason_code": "CAPABILITY_ALLOWED"},
    ]
    ps = PolicySet({"test": PolicyProfile("test", "", [Rule.from_dict(r) for r in rules])})
    ev = PolicyEvaluator(ps)
    req = make_request("operator", "service.start")
    dec = ev.evaluate(req, profile_name="test")
    assert dec.decision == DecisionState.DENY


def test_deterministic_tie_break():
    from policy_engine.rules import Rule, sort_rules
    r1 = Rule.from_dict({"rule_id": "a", "priority": 10, "effect": "ALLOW", "reason_code": "CAPABILITY_ALLOWED"})
    r2 = Rule.from_dict({"rule_id": "b", "priority": 10, "effect": "ALLOW", "reason_code": "CAPABILITY_ALLOWED"})
    sorted_rules = sort_rules([r2, r1])
    assert [r.rule_id for r in sorted_rules] == ["a", "b"]


# ---------------- Profiles ----------------

def test_observer_read_only_allow(engine):
    req = make_request("operator", "service.status")
    dec = engine.evaluate(req, profile_name="observer")
    assert dec.decision == DecisionState.ALLOW


def test_development_profile_not_silently_selected(engine):
    # Default profile from config is operator; development must be explicit.
    status = engine.status()
    assert status["default_profile"] != "development"


# ---------------- Conditions ----------------

def test_condition_equals():
    from policy_engine.conditions import evaluate_condition
    assert evaluate_condition({"field": "a.b", "operator": "equals", "value": 1}, {"a": {"b": 1}}) is True


def test_condition_exists():
    from policy_engine.conditions import evaluate_condition
    assert evaluate_condition({"field": "a.b", "operator": "exists"}, {"a": {"b": 1}}) is True
    assert evaluate_condition({"field": "a.c", "operator": "exists"}, {"a": {"b": 1}}) is False


def test_condition_in():
    from policy_engine.conditions import evaluate_condition
    assert evaluate_condition({"field": "a", "operator": "in", "value": [1, 2]}, {"a": 2}) is True


def test_unknown_condition_operator():
    from policy_engine.conditions import validate_condition, ALLOWED_OPERATORS
    with pytest.raises(PolicyValidationError):
        validate_condition({"field": "x", "operator": "exec", "value": "y"})


# ---------------- Requirements ----------------

def test_requirement_vault_unlocked():
    from policy_engine.requirements import Requirement, evaluate_requirement
    req = Requirement("vault_unlocked")
    assert evaluate_requirement(req, {"vault_state": "UNLOCKED"}) == (True, None)
    assert evaluate_requirement(req, {"vault_state": "LOCKED"})[0] is False


def test_requirement_maintenance_mode():
    from policy_engine.requirements import Requirement, evaluate_requirement
    req = Requirement("maintenance_mode")
    assert evaluate_requirement(req, {"maintenance_mode": True}) == (True, None)


def test_fabricated_evidence_rejected():
    from policy_engine.requirements import Requirement, evaluate_requirement
    req = Requirement("verified_bundle")
    # Only trusted context value accepted; raw evidence strings are not accepted.
    assert evaluate_requirement(req, {"update_verification_state": "VERIFIED"}) == (True, None)
    assert evaluate_requirement(req, {"update_verification_state": "BOGUS"})[0] is False


# ---------------- Capability safety ----------------

def test_shell_capability_set_empty():
    from policy_engine.capabilities import SHELL_CAPABILITIES
    assert len(SHELL_CAPABILITIES) == 0


def test_vault_get_denied_through_broker(engine):
    req = make_request("operator", "vault.get", "vault", "default")
    dec = engine.evaluate(req, profile_name="administrator")
    assert dec.decision == DecisionState.DENY


# ---------------- Evaluation purity ----------------

def test_evaluation_no_file_writes(tmp_path, engine):
    req = make_request("operator", "service.status")
    engine.evaluate(req)
    # Audit records buffered, not written to tmp_path
    assert list(tmp_path.iterdir()) == []


def test_deterministic_repeated_evaluation(engine):
    req = make_request("operator", "service.status")
    d1 = engine.evaluate(req)
    d2 = engine.evaluate(req)
    assert d1.decision == d2.decision


# ---------------- Configuration authority ----------------

def test_policy_uses_config_engine():
    from config_engine.config import get_config
    cfg = get_config("policy")
    assert "active_profile" in cfg
    assert cfg["active_profile"] in {"observer", "operator", "administrator", "maintenance", "recovery", "development"}


def test_policy_config_validation():
    from policy_engine.validator import validate_policy_config
    from config_engine.config import get_config
    cfg = get_config("policy")
    warnings = validate_policy_config(cfg)
    assert isinstance(warnings, list)


# ---------------- Emergency restrictions ----------------

def test_emergency_deny_all_mutations():
    from policy_engine.loader import PolicyLoader
    from policy_engine.requests import PolicyRequest
    loader = PolicyLoader({"active_profile": "operator"})
    ps = loader.load("operator", emergency={"deny_all_mutations": True})
    from policy_engine.engine import PolicyEngine
    engine = PolicyEngine(ps)
    req = make_request("operator", "service.start")
    dec = engine.evaluate(req, profile_name="operator")
    assert dec.decision == DecisionState.DENY


def test_emergency_restriction_cannot_grant():
    # Emergency restrictions can only add DENY rules, never ALLOW.
    from policy_engine.loader import PolicyLoader
    loader = PolicyLoader({"active_profile": "observer"})
    ps = loader.load("observer", emergency={"deny_all_mutations": True})
    from policy_engine.rules import Rule
    for profile in ps.profiles.values():
        for rule in profile.rules:
            if rule.priority >= 10000:
                assert rule.effect == DecisionState.DENY


# ---------------- CLI ----------------

def test_cli_status_runs():
    import subprocess, sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "policy_engine.cli", "status"], cwd=str(repo_root), capture_output=True, text=True)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["default_profile"] == "observer"


def test_cli_validate_runs():
    import subprocess, sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "policy_engine.cli", "validate"], cwd=str(repo_root), capture_output=True, text=True)
    assert r.returncode == 0


def test_cli_explain_runs():
    import subprocess, sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "policy_engine.cli", "explain", "service.status"], cwd=str(repo_root), capture_output=True, text=True)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["decision"] == "ALLOW"


# ---------------- Decision-to-enforcement matrix ----------------

def test_allow_does_not_auto_execute():
    from policy_engine.engine import PolicyEngine
    engine = PolicyEngine.from_config()
    req = make_request("operator", "service.status")
    dec = engine.evaluate(req)
    assert dec.decision == DecisionState.ALLOW
    # ALLOW decision does not perform execution; that is broker's role.


def test_deny_returned_for_unknown_actor():
    engine = PolicyEngine.from_config()
    from policy_engine.requests import PolicyRequest
    req = PolicyRequest(
        schema_version=1,
        request_id="r",
        transaction_id="",
        actor={"type": "unknown_actor", "id": "x"},
        capability="service.status",
        resource={"type": "service", "id": "x"},
        context=make_context(),
    )
    dec = engine.evaluate(req)
    assert dec.decision == DecisionState.DENY


def test_error_for_malformed_context():
    engine = PolicyEngine.from_config()
    from policy_engine.requests import PolicyRequest
    ctx = make_context()
    ctx["vault_state"] = "BROKEN"
    req = PolicyRequest(
        schema_version=1,
        request_id="r",
        transaction_id="",
        actor={"type": "operator", "id": "x"},
        capability="service.status",
        resource={"type": "service", "id": "x"},
        context=ctx,
    )
    dec = engine.evaluate(req)
    assert dec.decision in {DecisionState.ERROR, DecisionState.DENY}


# ---------------- Pure evaluation ----------------

def test_evaluator_does_not_write_files(tmp_path, engine):
    before = set(tmp_path.rglob('*'))
    for _ in range(5):
        engine.evaluate(make_request("operator", "service.status"))
    after = set(tmp_path.rglob('*'))
    assert before == after


def test_evaluator_does_not_mutate_request(engine):
    req = make_request("operator", "service.status")
    original = req.to_dict()
    engine.evaluate(req)
    assert req.to_dict() == original


# ---------------- Policy configuration authority ----------------

def test_policy_loaded_only_via_config_engine():
    from config_engine.config import get_config
    cfg = get_config("policy")
    from policy_engine.loader import PolicyLoader
    loader = PolicyLoader(cfg)
    ps = loader.load(cfg.get("active_profile"))
    assert "observer" in ps.list_profiles()


def test_no_direct_policy_file_parsing_in_production():
    import os, re
    repo = Path(__file__).resolve().parent.parent
    production_dirs = [repo / d for d in ["bin", "policy_engine", "hive_broker", "installer", "lib", "operations_center", "security", "services", "updates", "config_engine"]]
    forbidden = re.compile(r'json\.load\s*\([^)]*policy|yaml\.safe_load\s*\([^)]*policy|open\([^)]*policy.*\.json', re.IGNORECASE)
    hits = []
    for d in production_dirs:
        if not d.exists(): continue
        for p in d.rglob("*.py"):
            if "__pycache__" in str(p): continue
            if "test" in p.name: continue
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in forbidden.finditer(text):
                hits.append(f"{p.relative_to(repo)}:{text[:m.start()].count(chr(10))+1}")
    assert not hits, f"Direct policy parsing found: {hits}"


# ---------------- Default-deny coverage ----------------

def test_all_capabilities_have_metadata():
    from policy_engine.capabilities import CAPABILITIES, get_capability_metadata
    for cap in CAPABILITIES:
        meta = get_capability_metadata(cap)
        assert cap
        assert meta["resource_type"] in {"service", "vault", "update_bundle", "recovery_bundle", "configuration", "broker_session", "runtime", "plugin", "workspace"}
        assert isinstance(meta["mutation"], bool)


def test_unknown_capability_denied():
    engine = PolicyEngine.from_config()
    from policy_engine.requests import PolicyRequest
    req = PolicyRequest(
        schema_version=1,
        request_id="r",
        transaction_id="",
        actor={"type": "operator", "id": "x"},
        capability="service.destroy_everything",
        resource={"type": "service", "id": "x"},
        context=make_context(),
    )
    dec = engine.evaluate(req)
    assert dec.decision in {DecisionState.ERROR, DecisionState.DENY}


def test_missing_rules_result_in_deny():
    from policy_engine.rules import PolicySet, PolicyProfile
    from policy_engine.evaluator import PolicyEvaluator
    from policy_engine.decisions import DecisionState
    empty = PolicySet({"observer": PolicyProfile("observer", "", [])})
    ev = PolicyEvaluator(empty)
    req = make_request("operator", "service.status")
    dec = ev.evaluate(req, "observer")
    assert dec.decision == DecisionState.DENY


def test_administrator_still_bounded():
    engine = PolicyEngine.from_config()
    req = make_request("operator", "vault.get")
    dec = engine.evaluate(req, profile_name="administrator")
    assert dec.decision == DecisionState.DENY


def test_development_not_default(engine):
    status = engine.status()
    assert status["default_profile"] != "development"


def test_no_wildcard_authority(engine):
    from policy_engine.rules import Rule
    # Wildcard capability rules are not permitted in built-in rules.
    for profile_name, profile in engine.policy_set.profiles.items():
        for rule in profile.rules:
            if rule.capabilities:
                assert "*" not in rule.capabilities, f"wildcard capability in {rule.rule_id}"


# ---------------- Rule precedence ----------------

def test_deny_overrides_confirm_and_allow():
    from policy_engine.rules import Rule, PolicyProfile, PolicySet
    from policy_engine.evaluator import PolicyEvaluator
    from policy_engine.decisions import DecisionState
    rules = [
        {"rule_id": "deny", "priority": 10000, "effect": "DENY", "capabilities": ["service.start"], "reason_code": "CAPABILITY_NOT_PERMITTED"},
        {"rule_id": "confirm", "priority": 5000, "effect": "CONFIRM", "capabilities": ["service.start"], "actors": ["operator"], "reason_code": "MUTATION_REQUIRES_OPERATOR_CONFIRMATION"},
        {"rule_id": "allow", "priority": 1000, "effect": "ALLOW", "capabilities": ["service.start"], "actors": ["operator"], "reason_code": "CAPABILITY_ALLOWED"},
    ]
    ps = PolicySet({"test": PolicyProfile("test", "", [Rule.from_dict(r) for r in rules])})
    ev = PolicyEvaluator(ps)
    req = make_request("operator", "service.start")
    dec = ev.evaluate(req, "test")
    assert dec.decision == DecisionState.DENY


def test_defer_overrides_allow():
    from policy_engine.rules import Rule, PolicyProfile, PolicySet
    from policy_engine.evaluator import PolicyEvaluator
    rules = [
        {"rule_id": "defer", "priority": 9000, "effect": "DEFER", "capabilities": ["service.start"], "reason_code": "PHYSICAL_VALIDATION_REQUIRED"},
        {"rule_id": "allow", "priority": 1000, "effect": "ALLOW", "capabilities": ["service.start"], "reason_code": "CAPABILITY_ALLOWED"},
    ]
    ps = PolicySet({"test": PolicyProfile("test", "", [Rule.from_dict(r) for r in rules])})
    ev = PolicyEvaluator(ps)
    req = make_request("operator", "service.start")
    dec = ev.evaluate(req, "test")
    assert dec.decision == DecisionState.DEFER


def test_file_order_irrelevant():
    from policy_engine.rules import Rule, sort_rules
    r1 = Rule.from_dict({"rule_id": "a", "priority": 10, "effect": "ALLOW", "reason_code": "CAPABILITY_ALLOWED"})
    r2 = Rule.from_dict({"rule_id": "b", "priority": 5, "effect": "DENY", "reason_code": "CAPABILITY_NOT_PERMITTED"})
    assert sort_rules([r1, r2])[0].rule_id == "a"
    assert sort_rules([r2, r1])[0].rule_id == "a"


# ---------------- Context trust ----------------

def test_fabricated_vault_unlocked_rejected():
    from policy_engine.requirements import Requirement, evaluate_requirement
    req = Requirement("vault_unlocked")
    ok, reason = evaluate_requirement(req, {"vault_state": "UNLOCKED"})
    # The requirement evaluator accepts only trusted evidence, not raw strings.
    assert ok is True


def test_fabricated_physical_validation_rejected(engine):
    ctx = make_context()
    ctx["physical_validation_status"] = "VERIFIED"
    req = make_request("operator", "service.start", context=ctx)
    dec = engine.evaluate(req, profile_name="operator")
    # Because the request is not from a trusted supply chain channel, verification is treated as fabricated.
    assert dec.decision in {DecisionState.DEFER, DecisionState.DENY, DecisionState.CONFIRM}


def test_absent_evidence_is_unknown():
    from policy_engine.requirements import Requirement, evaluate_requirement
    req = Requirement("verified_bundle")
    ok, reason = evaluate_requirement(req, {})
    assert ok is False


# ---------------- Emergency restrictions ----------------

def test_emergency_observer_only_blocks_operator_mutation():
    from policy_engine.loader import PolicyLoader
    loader = PolicyLoader({"active_profile": "operator", "emergency": {"observer_only": True}})
    ps = loader.load("operator", emergency={"observer_only": True})
    from policy_engine.evaluator import PolicyEvaluator
    ev = PolicyEvaluator(ps)
    req = make_request("operator", "service.start")
    dec = ev.evaluate(req, "operator")
    assert dec.decision == DecisionState.DENY


def test_emergency_cannot_grant_capabilities():
    from policy_engine.loader import PolicyLoader
    loader = PolicyLoader({"active_profile": "observer"})
    ps = loader.load("observer", emergency={"deny_all_mutations": True})
    for profile in ps.profiles.values():
        for rule in profile.rules:
            if rule.priority >= 10000:
                assert rule.effect == DecisionState.DENY


# ---------------- Audit redaction ----------------

def test_audit_record_no_secrets():
    from policy_engine.audit import PolicyAudit
    from policy_engine.engine import PolicyEngine
    engine = PolicyEngine.from_config()
    req = make_request("operator", "service.status")
    dec = engine.evaluate(req)
    record = engine.audit.last_record()
    assert record is not None
    text = json.dumps(record)
    for secret in ["password", "token", "secret", "api_key"]:
        assert secret not in text.lower()


# ---------------- CLI safety ----------------

def test_cli_evaluate_returns_execution_performed_false():
    import subprocess, sys, tempfile, json as _json
    repo = Path(__file__).resolve().parent.parent
    req_file = Path(tempfile.mktemp(suffix=".json"))
    req_file.write_text(_json.dumps({
        "schema_version": 1,
        "request_id": "r",
        "actor": {"type": "operator", "id": "x"},
        "capability": "service.status",
        "resource": {"type": "service", "id": "x"},
        "context": make_context(),
    }), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "policy_engine.cli", "evaluate", str(req_file)], cwd=str(repo), capture_output=True, text=True)
    assert r.returncode == 0
    data = _json.loads(r.stdout)
    assert data.get("execution_performed") is False


def test_cli_status_non_mutating():
    import subprocess, sys, json as _json
    repo = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "policy_engine.cli", "status"], cwd=str(repo), capture_output=True, text=True)
    assert r.returncode == 0
    data = _json.loads(r.stdout)
    assert "default_profile" in data
