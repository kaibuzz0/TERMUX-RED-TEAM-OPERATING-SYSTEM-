# Termux / Android Portability Remediation Plan

## Linked audit findings

HRA-002, HRA-003, HRA-013, HRA-015, HRA-017

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

### REM-003: Implement proper Windows ACL snapshot/restore for transactional rollback

- **Priority:** P1
- **Blocks RC.2:** No
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `bootstrap/install_release.py`
  - `tests/test_bootstrap_finalization_transaction.py`
- **Implementation order:** 3
- **Tests required:**
  - test_bootstrap_finalization_transaction.py on Windows
  - test_bootstrap_finalization_transaction.py on Linux
  - New property test: rollback restores content and ACL-equivalent permissions
- **Rollback / failure handling:** Keep current best-effort chmod fallback behind a feature flag.
- **Android/Termux implications:** Termux uses POSIX permissions; this change must not regress Android behavior.
- **Release/signing implications:** None.
- **Acceptance criteria:**
  - Rollback test passes on Windows with exact permission-equivalence check
  - No regression on Linux/Termux
- **Suggested commit boundary:** `fix(bootstrap): preserve ACLs during transactional rollback on Windows`
- **Notes:** Use pywin32 or ctypes to snapshot/restore DACLs.

### REM-005: Refactor Supervisor path resolution to accept injectable roots

- **Priority:** P1
- **Blocks RC.2:** No
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `services/supervisor.py`
  - `lib/hive_path.py`
  - `tests/test_m19_malformed_input.py`
  - `tests/test_m19_e1_path_containment.py`
  - `tests/test_m19_corrupted_state.py`
- **Implementation order:** 5
- **Tests required:**
  - test_m19_malformed_input.py without monkeypatching _repo_root
  - All path-containment tests pass
- **Rollback / failure handling:** Restore monkeypatch-based test if constructor refactor breaks other consumers.
- **Android/Termux implications:** Path resolution is core to Android containment; no behavioral change expected.
- **Release/signing implications:** None.
- **Acceptance criteria:**
  - Supervisor accepts repository_root, config_root, etc. at construction
  - Module-level _repo_root remains as default but is not required
  - All tests use public constructor API
- **Suggested commit boundary:** `refactor(supervisor): inject path roots instead of module globals`
- **Notes:** Avoids the test-only monkeypatch and makes Supervisor testable.

### REM-006: Add regression test for restart crash-loop with window_seconds=0

- **Priority:** P0
- **Blocks RC.2:** Yes
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `services/restart.py`
  - `tests/test_m19_resource_exhaustion.py`
- **Implementation order:** 6
- **Tests required:**
  - New test: zero window enforces max_attempts crash loop
  - New test: positive window resets attempts after elapsed time
  - Full pytest suite
- **Rollback / failure handling:** The source fix is already committed; only adding tests, so revert test additions only.
- **Android/Termux implications:** Service restart policy directly affects Termux daemon behavior.
- **Release/signing implications:** None.
- **Acceptance criteria:**
  - Crash-loop test passes on both platforms
  - No behavior change beyond tests
- **Suggested commit boundary:** `test(restart): add regression tests for window=0 crash-loop enforcement`
- **Notes:** Source fix already done in audit phase; this locks in the contract.

### REM-008: Add CI matrix job for Termux/Android smoke tests

- **Priority:** P2
- **Blocks RC.2:** No
- **Dependencies:** REM-007
- **Files/modules affected:**
  - `.github/workflows/ci.yml`
  - `scripts/termux-smoke-test.sh (new)`
  - `README.md`
- **Implementation order:** 8
- **Tests required:**
  - Run install-termux-easy.sh in an Android emulator or Docker Termux image
  - Verify bootstrap finalization and restart policy behavior
- **Rollback / failure handling:** Allow job to be non-required (experimental) initially.
- **Android/Termux implications:** Directly validates Android install path; catch Path.home and permission regressions.
- **Release/signing implications:** None until smoke test becomes required.
- **Acceptance criteria:**
  - Termux smoke job runs green on PRs (may be non-blocking initially)
  - Job exercises install, finalization, and service restart
- **Suggested commit boundary:** `ci: add Termux smoke test matrix job`
- **Notes:** If GitHub Actions doesn't provide Termux runner, use a Docker image with proot/termux prefix.

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


## Additional Notes

Windows fixes are validated locally; Termux fixes are the production target. Use proot/Docker or an emulator for CI validation.
