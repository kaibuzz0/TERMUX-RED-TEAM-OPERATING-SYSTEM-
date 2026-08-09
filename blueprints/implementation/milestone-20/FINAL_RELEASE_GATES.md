# Hive OS Final 1.0.0 Release Gates

## Purpose

Planning document only. Milestone 20 is NOT yet authorized for implementation.

This document defines the minimum gates that must pass before Hive OS 1.0.0 can be declared a production release.

---

## Required Gates

### 1. Defects

| Severity | Required State |
|----------|---------------|
| BLOCKER | 0 |
| CRITICAL | 0 |
| HIGH | 0 or explicitly accepted with documented mitigation |
| MEDIUM | reviewed, none blocking |
| LOW | reviewed, tracked |

### 2. Continuous Integration

- All configured GitHub Actions jobs green
- No flaky-test regressions introduced since rc.1

### 3. Repository State

- clean working tree (no uncommitted changes)
- no staged files
- HEAD is a tagged release commit

### 4. Release Artifact

- built from final 1.0.0 tag
- artifact SHA-256 recorded
- manifest digest recorded
- metadata schema_version = 1
- reproducibility classification = CONTENT_REPRODUCIBLE or better

### 5. Release Notes

- `docs/releases/1.0.0.md` finalized
- known limitations explicitly listed
- no unsupported claims
- classification = PRODUCTION RELEASE

### 6. Production Signing

- owner-controlled offline Ed25519 signing ceremony performed
- public key in trust store
- private key never in repository
- artifact verified with public trust store
- tamper test passed
- key ID recorded

### 7. Accepted Android/Native-Termux Debt Review

- owner explicitly reviews the 12 accepted rc.1 limitations
- decides which (if any) must be resolved before 1.0.0
- documents decision for each item

### 8. RC Regression Check

- no defects discovered in rc.1 that require code changes
- if rc.2 or rc.3 is needed, all prior RC validation must be re-run

### 9. API/Schema Freeze

- no schema_version changes since rc.1
- no breaking API changes
- no new public-facing capabilities

### 10. No New Functionality

- no new subsystems
- no new features
- no new UI
- only fixes, documentation, and signing

---

## Authorization Required

Final 1.0.0 release requires explicit owner approval AFTER all gates above are satisfied.

Do NOT proceed to final release without:
- owner sign-off
- production signing ceremony completed
- final CI run green

---

*Planning document: 2026-08-09*
*Milestone 20: NOT YET AUTHORIZED*
