# Duplicate and Dead-Code Cleanup Plan

## Linked audit findings

HRA-017, HRA-018

## Items

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

### REM-009: Remove legacy Hive Ops duplicate entrypoints and consolidate canonical bin/hive

- **Priority:** P2
- **Blocks RC.2:** No
- **Dependencies:** REM-002, REM-005
- **Files/modules affected:**
  - `bin/hive`
  - `Hive Ops DevAI/bin/hive-os`
  - `Hive Ops Final/bin/hive`
  - `Hive Ops Final/original hive os complete/bin/hive`
  - `tests/test_canonical_source.py`
  - `canonical-source.json`
- **Implementation order:** 9
- **Tests required:**
  - test_canonical_source.py passes
  - New test: only canonical entrypoints exist
  - Install smoke test still launches the correct binary
- **Rollback / failure handling:** Move duplicates to an attic/deprecated directory rather than deleting if compatibility is uncertain.
- **Android/Termux implications:** Termux install scripts reference bin/hive; ensure canonical path stays valid.
- **Release/signing implications:** Release packaging must include only the canonical launcher.
- **Acceptance criteria:**
  - Single bin/hive and bin/hive-os (or documented aliases)
  - Legacy Hive Ops bin/ dirs removed or moved to blueprints/deprecated
- **Suggested commit boundary:** `cleanup: consolidate canonical launchers and remove legacy duplicates`
- **Notes:** Preserve historical files in blueprints/deprecated if they have documentation value.

### REM-010: Audit and remove hardcoded absolute paths from blueprints and docs

- **Priority:** P3
- **Blocks RC.2:** No
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `blueprints/**/*.md`
  - `MILESTONE*_REPORT.md`
  - `docs/**/*.md`
- **Implementation order:** 10
- **Tests required:**
  - New lint test: no /root/..., /home/..., or [A-Za-z]:\ paths in markdown source
  - Existing docs still render correctly
- **Rollback / failure handling:** Re-introduce specific paths in code blocks if they are examples.
- **Android/Termux implications:** Documentation should reference $HOME and Termux paths, not host-specific paths.
- **Release/signing implications:** None.
- **Acceptance criteria:**
  - Security scan finds zero hardcoded absolute paths outside examples
  - All examples are clearly marked as examples
- **Suggested commit boundary:** `docs: replace host-specific paths with parameterized examples`
- **Notes:** Add a CI lint step so this doesn't regress.


## Additional Notes

Use the duplicate map in evidence/duplicate_map.json to validate removal. Historical files can be moved to blueprints/deprecated rather than deleted.
