# RC.2 Acceptance Plan

## Linked audit findings

HRA-001, HRA-002, HRA-015, HRA-016, HRA-017

## Items

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

This is the final gate. It cannot start until REM-001, REM-002, REM-006, and REM-007 are merged.
