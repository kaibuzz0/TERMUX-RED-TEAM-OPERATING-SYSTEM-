# Concurrency and Service Lifecycle Remediation Plan

## Linked audit findings

HRA-005, HRA-015

## Items

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


## Additional Notes

Concurrency tests currently use local closures that fail on Windows spawn. Refactor to module-level workers or threading.
