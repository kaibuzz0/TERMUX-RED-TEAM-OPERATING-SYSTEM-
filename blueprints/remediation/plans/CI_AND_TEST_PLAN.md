# CI and Test Remediation Plan

## Linked audit findings

HRA-002, HRA-003, HRA-005, HRA-015, HRA-016

## Items

### REM-000: Establish controlled baseline and tool parity

- **Priority:** P0
- **Blocks RC.2:** Yes
- **Dependencies:** none
- **Files/modules affected:**
  - `.github/workflows/ci.yml`
  - `.github/workflows/rc2-candidate.yml`
  - `requirements-dev.txt`
  - `scripts/run_tests.sh`
- **Implementation order:** 0
- **Tests required:**
  - CI passes on ubuntu-latest with all 1463 tests
  - CI passes on windows-latest with expected 28 skips
  - Portable git and Python 3.11 env documented
- **Rollback / failure handling:** Revert workflow changes; keep local worktrees intact.
- **Android/Termux implications:** None directly; this enables reproducible validation of Android-targeted fixes.
- **Release/signing implications:** SHA-pinned CI is prerequisite for trustworthy release builds (enables HRA-016).
- **Acceptance criteria:**
  - Both branches green on CI before any further fix commits
  - README/CONTRIBUTING references CI matrix
- **Suggested commit boundary:** `ci: pin actions and document platform matrix`
- **Notes:** Do not start code fixes until CI baseline is reproducible.

### REM-004: Refactor concurrency tests to module-level workers or threading

- **Priority:** P2
- **Blocks RC.2:** No
- **Dependencies:** REM-000
- **Files/modules affected:**
  - `tests/test_m19_a1a3a4a5_real_concurrency.py`
  - `tests/test_m19_concurrent_registry_write.py`
  - `tests/test_m19_supervisor_concurrent_start_stop.py`
- **Implementation order:** 4
- **Tests required:**
  - All three concurrency tests pass on Windows spawn
  - All three pass on Linux fork
- **Rollback / failure handling:** Re-enable existing skip decorators if refactor introduces flakiness.
- **Android/Termux implications:** Threading model affects Android process limits; prefer threading over multiprocessing where possible.
- **Release/signing implications:** None.
- **Acceptance criteria:**
  - No local closures passed to multiprocessing
  - Tests run on both Windows and Linux CI
- **Suggested commit boundary:** `test: make concurrency tests portable across fork/spawn`
- **Notes:** Use `concurrent.futures.ThreadPoolExecutor` for in-process race tests; reserve multiprocessing for separate-process isolation tests.

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


## Additional Notes

The current suite passes 1463 tests with 28 Windows-only skips. The goal is to make CI green and reproducible, then shrink the skip set over time.
