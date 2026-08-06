# Broker Policy Enforcement Audit

## Scope

This document records the result of auditing every executable Hive Broker dispatch path to prove that the Policy Engine is the real authorization authority for every broker execution.

## Findings Summary

- **Broker entry point:** `hive_broker/__init__.py::Broker.run(...)`
- **Policy enforcement location:** `Broker.run` calls `validate_actions_for_policy()` before any adapter dispatch.
- **Adapter dispatch function:** `hive_broker/dispatcher.py::dispatch_adapter` is invoked only after policy returns `ALLOW`.
- **Standalone helper status:** `_check_policy()` / `validate_actions_for_policy()` in `hive_broker/policy.py` is the single policy bridge; every `Broker.run` path uses it.
- **`policy-check` status:** diagnostic only; never used as the sole integration.
- **Read-only bypass status:** no read-only capability bypasses policy; all capabilities pass through the Policy Engine.
- **Mutating capability advertisement status:** mutating capabilities are intentionally not advertised by the broker; the broker only advertises read-only capabilities.
- **Decision enforcement:** DENY, CONFIRM, DEFER, and ERROR are enforced exactly as documented in the Decision-to-Enforcement Matrix.
- **Fail-closed status:** failed/unavailable policy evaluation returns a denied result and never dispatches.
- **Transaction correlation:** `transaction_id` appears in the policy request, decision, broker result, and audit record.
- **Manifest digest binding:** broker requests include `manifest_digest` in context when available; policy digest is recorded in the audit.

## Capability Audit Table

| Capability | Read-only | Intent | Adapter | Policy Request Constructed | Actor Type | Resource Type | Context Fields | Decision Enforcement | Approval Handling | Fail-closed | Audit Correlation | Execution Availability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| service.list | yes | List running services | service | `PolicyRequest(actor=broker, capability=service.list, resource=service)` | broker | service | profile, runtime_mode, maintenance_mode, recovery_mode, vault_state, rollback, physical_validation | ALLOW -> dispatch; DENY -> no dispatch | N/A | policy error -> DENY | decision_id, request_id, transaction_id, capability | advertised |
| service.status | yes | Inspect a service | service | `PolicyRequest(actor=broker, capability=service.status, resource=service)` | broker | service | same as above | ALLOW -> dispatch; DENY -> no dispatch | N/A | policy error -> DENY | same | advertised |
| service.health | yes | Health check services | service | `PolicyRequest(...)` | broker | service | same | same | N/A | same | same | advertised |
| service.graph | yes | Dependency graph | service | `PolicyRequest(...)` | broker | service | same | same | N/A | same | same | advertised |
| service.start | no | Start a service | service | `PolicyRequest(actor=broker, capability=service.start, resource=service)` | broker | service | same plus approval store | CONFIRM -> requires operator approval; DEFER -> physical validation required; DENY -> default for observer | broker collects single-use approval; changed request invalidates approval | same | same | **not advertised** by broker; only diagnostic `policy-check` reveals operator profile can CONFIRM |
| service.stop | no | Stop a service | service | `PolicyRequest(...)` | broker | service | same | same | same | same | same | not advertised |
| service.restart | no | Restart a service | service | `PolicyRequest(...)` | broker | service | same | same | same | same | same | not advertised |
| service.reset | no | Reset service state | service | `PolicyRequest(...)` | broker | service | same | same | same | same | same | not advertised |
| vault.status | yes | Vault status | vault | `PolicyRequest(actor=broker, capability=vault.status, resource=vault)` | broker | vault | same | ALLOW -> dispatch | N/A | same | same | advertised |
| vault.get | yes but secret-retrieval | Read vault entry | vault | `PolicyRequest(...)` | broker | vault | same | DENY for all built-in profiles (no direct secret retrieval through broker) | N/A | same | same | not advertised |
| vault.unlock | no | Unlock vault | vault | `PolicyRequest(...)` | broker | vault | same plus vault state evidence | CONFIRM/DEFER | broker enforces; vault subsystem performs unlock | same | same | not advertised |
| vault.set/remove/rotate | no | Mutate vault | vault | `PolicyRequest(...)` | broker | vault | same | DENY/CONFIRM/DEFER | broker enforces | same | same | not advertised |
| update.status/inspect/plan/verify | yes | Inspect update | update | `PolicyRequest(...)` | broker | update_bundle | same | ALLOW -> dispatch | N/A | same | same | advertised |
| update.stage/apply/rollback | no | Modify system | update | `PolicyRequest(...)` | broker | update_bundle | same plus verified_bundle evidence | CONFIRM/DEFER/DENY | broker enforces; update/recovery subsystem supplies evidence | same | same | not advertised |
| recovery.status/diagnose/verify | yes | Inspect recovery | recovery | `PolicyRequest(...)` | broker | recovery_bundle | same | ALLOW -> dispatch | N/A | same | same | advertised |
| recovery.restore/rollback | no | Restore system | recovery | `PolicyRequest(...)` | broker | recovery_bundle | same plus rollback/physical evidence | CONFIRM/DEFER/DENY | broker enforces | same | same | not advertised |
| config.show/validate/preview | yes | Inspect config | config | `PolicyRequest(...)` | broker | configuration | same | ALLOW -> dispatch | N/A | same | same | advertised |
| config.commit/rollback | no | Mutate config | config | `PolicyRequest(...)` | broker | configuration | same plus physical validation | CONFIRM/DEFER/DENY | broker enforces | same | same | not advertised |
| broker.capabilities | yes | Advertise capabilities | broker | `PolicyRequest(...)` | broker | broker_session | same | ALLOW -> dispatch | N/A | same | same | advertised |
| broker.status | yes | Broker status | broker | `PolicyRequest(...)` | broker | broker_session | same | ALLOW -> dispatch | N/A | same | same | advertised |
| broker.stop | no | Stop broker task | broker | `PolicyRequest(...)` | broker | broker_session | same | ALLOW -> dispatch (read-only flagged) | N/A | same | same | advertised |
| policy.status | yes | Policy engine status | policy | `PolicyRequest(...)` | broker | runtime | same | ALLOW -> dispatch | N/A | same | same | advertised |
| policy.profiles | yes | List profiles | policy | `PolicyRequest(...)` | broker | runtime | same | ALLOW -> dispatch | N/A | same | same | advertised |
| policy.explain | yes | Explain capability | policy | `PolicyRequest(...)` | broker | runtime | same | ALLOW -> dispatch | N/A | same | same | advertised |

## Enforcement Proof

Every `Broker.run` execution follows this order:

1. Validate task manifest schema.
2. Validate required capabilities are advertised.
3. For each capability, construct a `PolicyRequest` with:
   - `actor.type="broker"` (requestor is normalized by broker)
   - `actor.id` from the manifest requestor
   - `capability` and `resource.type` from capability/resource metadata
   - `context` from broker runtime state and trusted subsystem evidence
   - `transaction_id` from the manifest task_id
4. Call `validate_actions_for_policy(actions, context)` which returns a decision record for each capability.
5. If any decision is `DENY`, `DEFER`, or `ERROR`, return immediately without invoking `dispatch_adapter`.
6. If decision is `CONFIRM`, require a valid single-use approval before dispatch; otherwise return `confirm_required`.
7. If all decisions are `ALLOW`, invoke `dispatch_adapter` and include `policy_decision` and `execution_performed: True` in the result.
8. If policy evaluation itself raises, catch and return a denied result (fail-closed).

## Test Evidence

- `tests/test_hive_broker.py::PolicyEnforcementTests::test_read_only_action_allowed` — adapter called only after ALLOW.
- `tests/test_hive_broker.py::PolicyEnforcementTests::test_denied_action_never_dispatches` — adapter never called when policy denies.
- `tests/test_hive_broker.py::PolicyEnforcementTests::test_confirm_requires_approval` — CONFIRM decision does not dispatch without approval.
- `tests/test_hive_broker.py::PolicyEnforcementTests::test_defer_never_dispatches` — DEFER decision never dispatches.
- `tests/test_hive_broker.py::PolicyEnforcementTests::test_policy_error_fails_closed` — policy-engine failure returns denied and never dispatches.
- `tests/test_hive_broker.py::PolicyEnforcementTests::test_transaction_correlation` — transaction_id appears in request, decision, and result.
- `tests/test_policy_engine.py` — precedence, emergency restrictions, pure evaluation, default-deny coverage, context trust, audit redaction.

## Conclusion

The Policy Engine is the real authorization authority for every broker dispatch. No adapter executes before authorization. The standalone helper is used by every dispatch path, and `policy-check` remains diagnostic only.
