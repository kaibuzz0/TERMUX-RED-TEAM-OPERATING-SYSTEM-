# Security Review

## Scope

Review security invariants, threat model, vault, agent broker, update trust, recovery, and policy enforcement.

## Findings

### Invariants
- Status: **PASS**. 12 invariants are defined, testable, and current compliance is labeled.

### Vault
- Status: **CONDITIONAL PASS**. Vault design acknowledges same-UID bypass and unlocked-memory risk. Requires Termux support verification for chosen crypto library.

### Agent broker
- Status: **PASS**. `max_delegations=0` and scoped paths are correct for initial release.

### Update trust
- Status: **PASS**. Staged, signed release archives replace raw `git pull`.

### Recovery
- Status: **PASS**. Tiered recovery with guarded Level 6.

### Policy enforcement boundary
- Status: **PASS**. BROKER-ENFORCED vs ADVISORY is clearly separated.

### Concerns
- `brain-plug/` Flask API has not been fully audited; should be isolated in `integrations/brain-plug/`.
- Some `hivedev-*` tools may bind listeners; need individual audit before merging into core/tools.

## Blockers

None for blueprint freeze.
