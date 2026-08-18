# Release and Bootstrap Remediation Plan

## Linked audit findings

HRA-001, HRA-002, HRA-015, HRA-016, HRA-017

## Items

### REM-001: Rewrite git history to remove HRA-001 key decoy from all history

- **Priority:** P0
- **Blocks RC.2:** Yes
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `Hive Ops DevAI/bin/hivedev-honey`
  - `.git/index (history rewrite)`
- **Implementation order:** 1
- **Tests required:**
  - git log --all --full-history -- Hive\ Ops\ DevAI/bin/hivedev-honey shows no key markers
  - truffleHog or git-secrets scan clean
  - re-run full pytest suite after rewrite
- **Rollback / failure handling:** Keep a pre-rewrite bare backup remote; if rewrite corrupts branches, restore from backup.
- **Android/Termux implications:** None, but any Termux clone from this repo will inherit rewritten history.
- **Release/signing implications:** Historical release tags must be re-signed or re-tagged after rewrite; notify all forks.
- **Acceptance criteria:**
  - No BEGIN/END PRIVATE KEY strings in any commit reachable from master or bootstrap
  - All tests still pass
- **Suggested commit boundary:** `security: remove historical key decoy markers via filter-repo`
- **Notes:** Coordinate with repo owner before force-pushing rewritten history.

### REM-002: Consolidate and rotate trust_store / release PEM artifacts

- **Priority:** P1
- **Blocks RC.2:** No
- **Dependencies:** REM-001
- **Files/modules affected:**
  - `releases/1.0.0/hive-release.pem`
  - `updates/trust_store/hive-release.pem`
  - `release_engine/verifier.py`
  - `updates/manifest.py`
  - `bootstrap/install_release.py`
- **Implementation order:** 2
- **Tests required:**
  - test_m20_1_trust_store_integrity.py
  - test_m20_trust_anchor_hardening.py
  - test_bootstrap_install_release.py
  - test_sha256_integrity.py
  - New test: only one hive-release.pem exists and is loaded
- **Rollback / failure handling:** Keep old PEM in a signed archive outside the repo; revert to two copies if tooling isn't updated.
- **Android/Termux implications:** Termux update path must use the single trust anchor; verify on-device install/update.
- **Release/signing implications:** All future releases must be signed by the consolidated key; old releases need re-verification metadata.
- **Acceptance criteria:**
  - Exactly one hive-release.pem in the repo
  - Update and release verifiers both load the same path
  - Legacy duplicate files removed
- **Suggested commit boundary:** `security: consolidate trust anchor and remove duplicate release PEM`
- **Notes:** Consider key rotation if the old key touched the hivedev tooling.

### REM-007: Pin all GitHub Actions to SHA and add dependency update automation

- **Priority:** P1
- **Blocks RC.2:** No
- **Dependencies:** REM-000, REM-001
- **Files/modules affected:**
  - `.github/workflows/ci.yml`
  - `.github/workflows/command-site-snapshot.yml`
  - `.github/workflows/rc1-baseline-audit.yml`
  - `.github/workflows/rc2-candidate.yml`
  - `.github/dependabot.yml (new)`
- **Implementation order:** 7
- **Tests required:**
  - Workflows still pass after SHA pinning
  - Dependabot opens a test PR for an action update
- **Rollback / failure handling:** Revert to floating tags if SHA maintenance becomes unmanageable (not recommended).
- **Android/Termux implications:** None.
- **Release/signing implications:** Build reproducibility and supply-chain integrity improved.
- **Acceptance criteria:**
  - No workflow uses a floating major tag
  - Every action has '# vX.Y.Z' comment
  - CI green after change
- **Suggested commit boundary:** `ci: pin third-party actions to SHA and enable dependabot updates`
- **Notes:** Use official action commit SHAs from GitHub.

### REM-011: Run final RC.2 acceptance gate and generate signed release notes

- **Priority:** P0
- **Blocks RC.2:** Yes
- **Dependencies:** REM-001, REM-002, REM-006, REM-007
- **Files/modules affected:**
  - `RELEASE_NOTES.md`
  - `version.py`
  - `.github/workflows/rc2-candidate.yml`
- **Implementation order:** 11
- **Tests required:**
  - Full pytest suite: 1463 passed, expected skips
  - TruffleHog / git-secrets clean
  - CI matrix green (ubuntu, windows, termux-smoke optional)
  - Manual sign/verify round-trip on a release artifact
- **Rollback / failure handling:** Tag RC.2 as pre-release; do not promote to stable until acceptance criteria met.
- **Android/Termux implications:** Final install/finalization test on Termux before tagging.
- **Release/signing implications:** Release notes must reference trust anchor path and key fingerprint.
- **Acceptance criteria:**
  - All RC.2-blocking findings closed
  - No open High/Critical findings
  - Signed release artifact verifies with consolidated trust anchor
- **Suggested commit boundary:** `release: tag v2.0.0-rc2 and publish signed release notes`
- **Notes:** This is the final gate; do not tag until all P0/P1 items are merged.


## Additional Notes

The bootstrap and release paths share a single trust anchor. Consolidation must happen before any V2 artifact is signed.
