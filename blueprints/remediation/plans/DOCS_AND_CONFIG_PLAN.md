# Documentation and Configuration Remediation Plan

## Linked audit findings

HRA-002, HRA-003, HRA-015, HRA-018

## Items

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

Add a lint rule to prevent hardcoded absolute paths in new documentation and examples.
