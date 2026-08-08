# Milestone 19 — Production Hardening / Release Candidate Plan

## Baseline
- **Commit:** 1b063d09207c3faa256b9734584ce151e30c7042
- **Target:** Hive OS 1.0.0-rc.1
- **Rule:** Feature freeze ACTIVE. No new product functionality.

## Architecture Reality Check

The canonical Hive OS codebase (verified at 1b063d0) uses these actual mechanisms:
- **Concurrency:** Directory-based `FileLock` in `config_engine/persistence.py` — NOT threading/RLock
- **KDF bounds:** `hashlib.scrypt` internal `maxmem` parameter — NO standalone memory limiter
- **Logging:** No rotation in canonical `services/` — only in legacy `Hive Ops Final/`
- **Sandbox:** Process-level isolation via broker/policy — NO kernel containment (seccomp/Landlock/SELinux explicitly rejected per ADR-0009)
- **Bundle extraction:** Rejects symlinks, hardlinks, devices, FIFOs, sockets
- **YAML parsing:** `yaml.safe_load` only — no unsafe parser
- **Policy:** Default deny with deterministic precedence (DENY > ERROR > DEFER > CONFIRM > ALLOW)
- **Vault:** AES-256-GCM + scrypt + HKDF-SHA256, atomic writes

Do NOT test mechanisms that do not exist. Do NOT introduce new mechanisms to make rows testable.

---

## 1. APPROVED ATTACK AREAS

### AREA A: FILELOCK RACES (Real Concurrency Mechanism)

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| A1 | Concurrent config commits race | `ConfigurationStore.save_committed()` | HIGH | Spawn concurrent processes; verify one succeeds |
| A2 | Stale lock detection/recovery | `FileLock.__enter__()` timeout | HIGH | Simulate stale lock; verify timeout and recovery |
| A3 | Lock not released on exception | `FileLock.__exit__()` | MEDIUM | Force exception inside `with`; verify cleanup |
| A4 | Concurrent activation attempts | `ActiveState.acquire_lock()` | HIGH | Two processes, same lock; verify second blocked |
| A5 | Lock directory left after crash | `FileLock` cleanup | MEDIUM | Simulate crash while holding lock; verify recovery |

### AREA B: MALFORMED INPUT / PARSING

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| B1 | Deeply nested JSON | `json.loads` throughout | MEDIUM | 1000+ nested objects; verify graceful failure |
| B2 | Invalid UTF-8 in configs | `config_engine/loader.py` | MEDIUM | Invalid byte sequences; verify error |
| B3 | Path traversal variants | `services/supervisor.py:_resolve_path()` | HIGH | `....//`, `%2e%2e`, null bytes; verify rejection |
| B4 | Symlink in working directory | `services/supervisor.py` | HIGH | Symlink as cwd; verify containment |
| B5 | Zip bomb in update bundle | `updates/bundle.py` | HIGH | Oversized/compressed; verify size enforcement |
| B6 | Integer overflow in sequence | `updates/metadata.py` | MEDIUM | Boundary at max int; verify safe handling |
| B7 | Empty/corrupted policy JSON | `policy_engine/loader.py` | MEDIUM | Empty ruleset; verify DEFAULT_DENY |

### AREA C: AUTHORIZATION / BROKER BYPASS

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| C1 | Caller-supplied context trust | `policy_engine/evaluator.py:_validate_request()` | HIGH | Fabricated context; verify `CONTEXT_SCHEMA` rejection |
| C2 | Policy bypass via empty rules | `policy_engine/evaluator.py:_resolve()` | MEDIUM | Empty rule set; verify DEFAULT_DENY |
| C3 | Transaction ID collision | `hive_broker/transaction.py` | MEDIUM | Verify UUID4 uniqueness |
| C4 | Adapter direct call bypass | `hive_broker/adapters.py` | HIGH | Verify `dispatch_adapter` requires broker gate |
| C5 | Emergency restriction bypass | `policy_engine/loader.py:_emergency_rules()` | CRITICAL | Verify emergency cannot grant capabilities |
| C6 | Confirm without approval | `installer/activate.py:activate()` | HIGH | Missing `--approve`; verify blocked |
| C7 | Broker session impersonation | `hive_broker/session.py` | MEDIUM | Verify unguessable session IDs |

### AREA D: CORRUPTED STATE / FILESYSTEM

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| D1 | Corrupt active pointer | `installer/activate.py:_active_pointer()` | CRITICAL | Corrupt JSON; verify error + recoverable |
| D2 | Corrupt release metadata | `installer/activate.py:_read_release_metadata()` | CRITICAL | Corrupt JSON; verify no silent activation |
| D3 | Stale lock file | `installer/activate.py:_read_lock()` | HIGH | Verify stale detection + force recovery |
| D4 | Partial config write | `config_engine/persistence.py:atomic_write_json()` | HIGH | Verify `write-to-temp + replace` atomicity |
| D5 | Symlink in state directory | Path resolution throughout | HIGH | Test `resolve()` with symlinks |
| D6 | Config history corruption | `ConfigurationStore.list_transactions()` | MEDIUM | Corrupted `.record.json`; verify skipped not fatal |
| D7 | Release runtime escapes data root | `installer/activate.py:activate()` | HIGH | Verify `relative_to()` containment |

### AREA E: SUPPLY CHAIN / SIGNING

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| E1 | Trust store tampering | `updates/trust.py:TrustStore` | CRITICAL | Verify read-only after load |
| E2 | Wrong key type | `release_engine/signing.py:load_private_key()` | CRITICAL | RSA key; verify rejection |
| E3 | Signature algorithm downgrade | `updates/signing.py:verify_metadata()` | CRITICAL | Verify Ed25519 enforced |
| E4 | Manifest digest mismatch | `release_engine/verifier.py` | MEDIUM | Tampered manifest; verify rejection |
| E5 | Bundle extraction path traversal | `updates/bundle.py` | HIGH | `../escape` tar member; verify rejection |
| E6 | Emergency bundle bypass | `updates/verifier.py:verify(allow_emergency=True)` | HIGH | Verify flag required + logged |

### AREA F: RECOVERY GUARANTEES

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| F1 | Journal replay after crash | `installer/journal.py:InstallJournal` | HIGH | Verify idempotent replay |
| F2 | Rollback atomicity | `installer/activate.py:rollback()` | CRITICAL | Verify pointer + metadata consistency |
| F3 | Config rollback completeness | `config_engine/persistence.py:rollback_to()` | HIGH | Verify committed == snapshot |
| F4 | Service restart after crash | `services/restart.py:RestartPolicy` | MEDIUM | Verify backoff + max restart limits |
| F5 | Vault backup/restore | `security/vault/` | HIGH | Verify backup decrypts to identical plaintext |

### AREA G: API / SCHEMA COMPATIBILITY

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| G1 | Schema version downgrade | All `schema_version` fields | MEDIUM | Version mismatch; verify error |
| G2 | Missing required field | All dataclass parsers | MEDIUM | `KeyError` → error, not crash |
| G3 | Unknown field injection | JSON config loading | LOW | Verify ignore or warn |
| G4 | CLI backward compatibility | `bin/hive` | MEDIUM | Verify existing flags parse |

### AREA H: RESOURCE EXHAUSTION (Real Bounds)

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| H1 | KDF memory exhaustion | `security/vault/crypto.py:derive_key()` | HIGH | Verify `maxmem` rejects excessive params |
| H2 | Config history unbounded growth | `config_engine/persistence.py` | MEDIUM | Verify no auto-pruning; document limit |
| H3 | Broker transaction accumulation | `hive_broker/session.py` | MEDIUM | Verify `max_active_transactions:10` enforced |
| H4 | Service restart loop | `services/restart.py` | MEDIUM | Verify max restart count + backoff |
| H5 | Policy rule explosion | `policy_engine/evaluator.py` | MEDIUM | Verify MAX_RULES=1024 enforced |

### AREA I: SECURITY REGRESSION

| # | Attack Vector | Location | Severity | Test Approach |
|---|--------------|----------|----------|---------------|
| I1 | Secret in audit record | `config_engine/persistence.py:_redact_record()` | CRITICAL | Verify `[REDACTED]` |
| I2 | Vault password in argv | `security/vault/cli.py` | HIGH | Verify prompt, not argv |
| I3 | Environment passthrough | `services/supervisor.py:_build_environment()` | MEDIUM | Verify only allowed env vars pass |
| I4 | Temporary file exposure | `atomic_write_json` temp files | MEDIUM | Verify private directory |
| I5 | Process group signal isolation | `services/supervisor.py:start()` | HIGH | Verify `start_new_session` isolates signals |

### AREA J: MILESTONE 18 DEBT REDUCTION

| # | Debt Item | Can Reduce? | Approach |
|---|-----------|-------------|----------|
| J1 | Native Termux shell smoke | NO | Document PRoot limitation |
| J2 | Termux process restart | YES | Add FileLock persistence test |
| J3 | Android app process death | NO | Document as accepted RC risk |
| J4 | Device reboot | NO | Document as accepted RC risk |
| J5 | Battery/thermal | NO | Document as accepted RC risk |
| J6 | Permission failure (root/PRoot) | PARTIAL | Add synthetic unwritable-directory fixture |
| J7 | Real rollback interruption | PARTIAL | Add deterministic `raise` failpoint in test |
| J8 | Simulated interruption | YES | Add property-based atomic write test |
| J9 | Offline by inspection | YES | Add `socket` monkeypatch test |

---

## 2. RELEASE-BLOCKING CRITERIA

**BLOCKER:**
- Unauthorized privilege escalation
- Policy/broker bypass
- Vault plaintext exposure
- Unverified release activation
- Data loss during normal rollback
- Fails closed preventing recovery
- Regression in existing 537 tests
- Weakening of security parameters

**CRITICAL:**
- Resource exhaustion without bounds
- State corruption persisting across restarts
- Bypass of explicit approval
- Silent failure of security checks

**Milestone 19 cannot pass with unresolved BLOCKER or CRITICAL.**

---

## 3. EXPLICITLY WILL NOT CHANGE

- No new CLI commands or subsystems
- No changes to KDF parameters
- No weakening of permission models
- No new plugin capabilities
- No new release channels
- No UI/dashboard changes
- No documentation expansion beyond security/runbook notes
- No changes to CI test matrix
- No support for new Python versions
- No changes to legacy compatibility bridge

---

## 4. IMPLEMENTATION PRIORITY

### Phase 1: Lock Races, Authorization, Security Regression
- A1–A5: FileLock concurrency
- C1–C7: Authorization bypass
- I1–I5: Security regression

### Phase 2: State Corruption, Recovery, Malformed Input
- D1–D7: Corrupted state
- F1–F5: Recovery guarantees
- B1–B7: Malformed input

### Phase 3: Supply Chain, Resource, Schema
- E1–E6: Signing/trust
- H1–H5: Resource bounds
- G1–G4: Schema compatibility

### Phase 4: Debt Reduction & RC Prep
- J1–J9: Where reducible
- Final regression: 537 tests must pass
- Performance: no >10% regression

---

## 5. STOP FOR REVIEW

This plan is complete and awaits owner approval.
Do not begin implementation changes until approved.
