# Master Remediation Plan

**Issue:** #7 — BUILD REMEDIATION BLUEPRINTS  
**Follows:** Issue #6 — HERMES Full Repository Audit  
**Repo:** https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-  
**Branches:** `master` (d173d2f), `hive-1.1-rc2-bootstrap` (fa0f917)  

## Purpose

This is the top-level remediation plan that binds all domain-specific plans to the audit findings. It defines execution order, dependencies, rollback strategy, and the RC.2 acceptance gate.

## Remediation Philosophy

1. **Audit first, blueprint second, code third.** No code changes happen during the blueprint phase.
2. **Security / trust fixes precede everything else.** You cannot safely ship a release if history contains secret-shaped artifacts or trust anchors are duplicated.
3. **CI baseline must be green and reproducible before any fix lands.** That prevents "works on my machine" regressions.
4. **Every fix must have a test that fails before the fix and passes after.** This is the definition of done for each remediation item.
5. **Fix passes are bounded.** Each REM item is one focused commit (or one PR). No giant omnibus commits.

## Execution Order

```text
Phase 0: Baseline & CI parity           (REM-000)
Phase 1: Security & trust hardening    (REM-001, REM-002)
Phase 2: Core correctness/portability  (REM-003, REM-004, REM-005, REM-006)
Phase 3: CI / release infrastructure   (REM-007, REM-008)
Phase 4: Cleanup, dead-code, docs      (REM-009, REM-010)
Phase 5: RC.2 acceptance               (REM-011)
```

## Blockers for RC.2

The following remediation items **must** be complete before declaring V2/RC.2:

- REM-000 — reproducible CI baseline
- REM-001 — historical key decoy removed from git history
- REM-006 — restart crash-loop regression tests
- REM-011 — final acceptance gate

## Dependency Graph

- `REM-000` depends on: none
- `REM-001` depends on: REM-000
- `REM-002` depends on: REM-001
- `REM-003` depends on: REM-000
- `REM-004` depends on: REM-000
- `REM-005` depends on: REM-000
- `REM-006` depends on: REM-000
- `REM-007` depends on: REM-000, REM-001
- `REM-008` depends on: REM-007
- `REM-009` depends on: REM-002, REM-005
- `REM-010` depends on: REM-000
- `REM-011` depends on: REM-001, REM-002, REM-006, REM-007

## Cross-Cutting Concerns

- **Android / Termux:** All path, permission, and service-lifecycle fixes must be validated in a Termux-like environment. POSIX semantics are the production norm; Windows is the development/portability edge case.
- **Release / signing:** Trust anchor consolidation (REM-002) and action SHA pinning (REM-007) are prerequisites for any signed release build.
- **Rollback:** Every remediation item has a documented rollback. If a fix breaks CI or Termux validation, revert that item and its dependent items, not the whole branch.

## Sign-Off Criteria

- [ ] All P0 items merged to both branches
- [ ] All RC.2-blocking items closed
- [ ] Full test suite green on ubuntu-latest and windows-latest
- [ ] TruffleHog / git-secrets scan clean
- [ ] Signed release artifact verifies with the consolidated trust anchor
- [ ] Issue #7 closed and Issue #8 (execution) opened with the first bounded fix pass
