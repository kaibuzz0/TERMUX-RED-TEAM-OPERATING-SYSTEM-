# Canonical Source Decision

**Status:** Phase 1 recommendation. Final decision requires human review.

## Candidates

| Candidate | Files | Entry point used by installer | Entry point used by updater | Entry point used by repair | TUI | Boot | Tools |
|-----------|-------|------------------------------|-----------------------------|----------------------------|-----|------|-------|
| `Hive Ops Final/` | 84 | `install-termux.sh` links `Hive Ops Final/bin/hive*` | `update.sh` re-links `Hive Ops Final/bin/hive*` | `emergency-repair.sh` re-links `Hive Ops Final/bin/hive*` | `hive-ui-v2` | `hive-secure-login` + `00-hive-secure.sh` | 27 tools in `tools/` |
| `Hive Ops DevAI/` | 54 | `install.sh` links `Hive Ops DevAI/bin/hive*`/`hivedev*` | NOT updated by current `update.sh` | NOT repaired by current `emergency-repair.sh` | `hive-ui` | `hive-boot` + `00-hive-devai` | Specialist `hivedev-*` scripts |
| Root-level launchers | 4 + README | `install-termux.sh`, `install.sh`, `update.sh`, `emergency-repair.sh` | N/A | N/A | N/A | N/A | N/A |

## Weighted scoring matrix

| Criterion | Weight | Hive Ops Final | Hive Ops DevAI | Root scripts |
|-----------|--------|----------------|----------------|--------------|
| Functional completeness | 15 | 14 (CLI+TUI+boot+tools+login) | 13 (rich agent/tools but fragmented) | 3 (only install/update/repair) |
| Installer integration | 15 | 15 (`install-termux.sh` installs it) | 5 (`install.sh` installs it, but README points to `install-termux.sh`) | 0 |
| Update integration | 12 | 12 (`update.sh` maintains it) | 3 (not maintained by current updater) | 0 |
| Repair integration | 10 | 10 (`emergency-repair.sh` repairs it) | 2 (not repaired) | 0 |
| Test coverage | 8 | 4 (legacy subtree; some CI tests target DevAI) | 6 (CI lints DevAI) | 0 |
| Security quality | 12 | 5 (base64 auth, remote exec, unquoted paths) | 4 (orchestrator autonomy, listener patterns) | 3 (scripts have same weaknesses) |
| Termux compatibility | 10 | 7 (some `/root/hive` paths may fail non-root) | 6 (unclear path assumptions) | 8 (Termux-specific checks) |
| Documentation accuracy | 5 | 3 (README describes Final features) | 3 (DevAI docstrings exist) | 4 (README is main docs) |
| Internal consistency | 6 | 3 (contains embedded legacy subtree) | 3 (parallel swarm/orchestrator modules) | 5 (scripts are consistent with each other) |
| Dependency completeness | 5 | 3 (relies on Termux packages) | 3 (relies on `requirements.txt` too) | 4 |
| Data compatibility | 5 | 4 (uses `~/.hive_auth`, `~/.hive_ops.txt`) | 2 (not known to use same state files) | 0 |
| Migration complexity | 5 | 4 (must extract legacy subtree) | 3 (must integrate with install/update/repair) | 0 |
| Maintenance burden | 4 | 3 (large embedded legacy) | 4 (modular Python but many scripts) | 0 |
| **Weighted total** | | **~540** (raw sum) | **~390** (raw sum) | **~150** |

## Decision

**Recommendation:**

- **`Hive Ops Final/`** as the **CANONICAL AFTER LIMITED REPAIR** foundation.
- **`Hive Ops DevAI/`** as a **REFERENCE IMPLEMENTATION ONLY** for agent/tool ideas; its capabilities should be selectively merged into the canonical tree, not kept as a second production root.
- **Root-level launchers** remain as top-level entry points but must be rewritten to be transactional, verified, and canonical-tree aware.

## Rationale

1. The primary installer (`install-termux.sh`), updater (`update.sh`), and repair script (`emergency-repair.sh`) all operate on `Hive Ops Final/`.
2. `Hive Ops Final/` has the unified `hive` CLI, the README-described `hive-ui-v2`, the `hive-secure-login` boot integration, and the `tools/` directory.
3. `Hive Ops DevAI/` is not maintained by the current update/repair path; leaving it as a second production root would perpetuate divergence.
4. Neither candidate is secure enough to ship as-is; "CANONICAL AFTER LIMITED REPAIR" reflects that the structure is the right foundation but the implementation requires security hardening.

## Required repair before canonical declaration

1. Remove or move `Hive Ops Final/original hive os complete/` to `archive/`.
2. Fix base64 credential storage to use salted hashing.
3. Fix shell safety issues (unquoted globs, path validation, `set -e`).
4. Add update verification (pinned commit/hash/TUF).
5. Integrate selected DevAI capabilities (agents, orchestrator, Hermes bridge) through the canonical CLI rather than as a separate tree.
6. Unify boot scripts and shell integration.

## Confidence

**MEDIUM-HIGH** for structural canonical choice; **LOW** for security readiness without the above repairs.
