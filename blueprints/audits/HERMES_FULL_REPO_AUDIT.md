# HERMES Full Repository Audit

**Repository:** https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-  
**Branches audited:** `master` (d173d2f) and `hive-1.1-rc2-bootstrap` (fa0f917)  
**Audit date:** 2026-08-18T01:46:11.282686+00:00

## Executive Summary

This audit covered both active branches of the Hive OS / Termux Red Team Operating System repository. A hard-stop finding (HRA-001) was discovered immediately: a fake/placeholder RSA private key block embedded in a honeytrap helper. After removing it, the audit continued and fixed a broad set of Windows/CI portability bugs, a restart-policy logic flaw, and test-correctness issues.

- **Total findings:** 18
- **Severity:** Critical 1, High 3, Medium 9, Low 5
- **Findings that block V2/RC.2:** 3
- **Findings fixed this round:** 13
- **Open / partially open:** 4

### Test Results (after fixes)

| Branch | Passed | Skipped | Failed |
|---|---|---|---|
| master | 1463 | 28 | 0 |
| hive-1.1-rc2-bootstrap | 1463 | 28 | 0 |

The 28 skipped tests on each branch are POSIX-only (symlinks without privileges, bash contract tests, exact POSIX mode checks) and are expected on Windows.

## Branch Divergence Map

`master` is one commit ahead of `hive-1.1-rc2-bootstrap` because `master` retains `.github/workflows/command-site-snapshot.yml`, which the bootstrap branch deleted. After the audit fix commits, the only remaining content differences are:

- `.github/workflows/command-site-snapshot.yml` (present on master, absent on bootstrap)
- Minor test skip wording differences introduced by separate commits

Both branches now share identical source fixes for all runtime/test bugs addressed.

## Duplicate / Divergence Artifacts

A SHA-256 duplicate scan found byte-identical files within and across branches. Highlights:

- `releases/1.0.0/hive-release.pem` == `updates/trust_store/hive-release.pem` (4 copies total across branches)
- Multiple `bin/hive` / `hive-os` launchers in `bin/`, `Hive Ops DevAI/bin/`, `Hive Ops Final/bin/`, and legacy `Hive Ops Final/original hive os complete/bin/`

These duplicates create an ambiguous canonical entrypoint and enlarge the trust boundary. Consolidation is recommended before V2.

## Dead / Stale Code Candidates

- `Hive Ops DevAI/bin/hivedev-honey` (key-decoy file, already cleaned)
- Legacy `Hive Ops Final/original hive os complete/` tree
- `brain-plug/` documentation (referenced only in grep exclusions)
- Duplicated `bin/hive` scripts across `Hive Ops */bin/`

## CI Health

- All `.github/workflows/*.yml` use floating `actions/checkout@v4` tags without SHA pins (HRA-016). This violates the repository's own dependency-pinning posture.
- Workflows are not exercised in this environment (no Linux runner available), but the test suite now passes on a clean Windows Python checkout with the portable git toolchain.

## Termux / Android Portability

- `Path.home()` was fixed to honor `$HOME`, which is critical for Termux where `$HOME` is `/data/data/com.termux/files/home`.
- POSIX-mode assertions are now gated on non-Windows platforms, preventing false-red CI on Android-derived test runs.
- The restart-policy fix (HRA-015) directly affects Termux service lifecycle behavior.

## Release / Security Chain Assessment

- HRA-001 key decoy has been removed from current branch HEAD, but history still contains it. A `git filter-repo` or BFG rewrite is recommended if the repository was ever scanned as a real secret.
- Duplicate `hive-release.pem` files need consolidation and rotation if any real signing key was ever generated from the hivedev tooling.
- GitHub Actions must be SHA-pinned before declaring V2/RC.2 production-ready.

## Prioritized Remediation Queue

1. **HRA-001** — Decide whether to rewrite git history to remove the key decoy permanently.
2. **HRA-015** — Already fixed; add a regression test for `window_seconds=0` crash-loop enforcement.
3. **HRA-002** — Already fixed; verify on a real Termux device.
4. **HRA-016** — Pin all GitHub Actions to SHA + version comment.
5. **HRA-017** — Consolidate trust_store and canonical `bin/hive`; remove legacy Hive Ops duplicates.
6. **HRA-003** — Implement Windows ACL snapshot/restore for transactional rollback.
7. **HRA-018** — Add lint rule to block hardcoded absolute paths in new code.
8. **HRA-004 follow-up** — Refactor concurrency tests to module-level workers so they can run on Windows spawn.

## Detailed Findings

### HRA-001: Fake/placeholder RSA private key markers committed in hivedev-honey honeytrap

- **Severity:** Critical
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** Yes
- **Status:** Fixed in both branches.

**Evidence:** Hive Ops DevAI/bin/hivedev-honey contained literal '[REDACTED_KEY_MARKER]' block around line 193 with a [REDACTED PRIVATE KEY] placeholder. Also duplicated in both branches.

**Impact:** If any downstream tooling or user mistakes the placeholder for a real key and reuses the structure, it trains a harmful pattern. Presence of private-key markers in source control triggers secret-scanning alerts and breaks zero-trust posture.

**Likely root cause:** A helper/honeytrap binary embedded key-shaped decoy material instead of generating keys at runtime or referencing a key-management command.

**Suggested remediation:** Removed the BEGIN/END markers and replaced the literal block with a clear comment indicating it was a decoy. Rotate any real signing keys that may have been generated from this tooling; audit trust_store and release PEMs for linkage.

---

### HRA-002: Path.home() ignores $HOME on Windows, breaking Termux finalization snapshots

- **Severity:** High
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** Yes
- **Status:** Fixed.

**Evidence:** bootstrap/install_release.py _termux_finalization_snapshots() used Path.home() to locate .bashrc and .config. On Windows, Path.home() reads USERPROFILE/HOMEDRIVE, not $HOME.

**Impact:** Rollback restores the wrong files on Windows; on Termux/Android the same issue can occur if $HOME is overridden. Tests that monkeypatch HOME silently test the wrong target.

**Likely root cause:** Cross-platform home-dir resolution assumed Python's Path.home() honors $HOME; it does not on Windows.

**Suggested remediation:** Derive home from os.environ.get('HOME') first, then fall back to Path.home(). Patched in both branches.

---

### HRA-003: File-snapshot rollback may not restore permissions on Windows

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Partially fixed (best-effort).

**Evidence:** bootstrap/install_release.py _restore_file_snapshot uses os.replace(temp, path) and then path.chmod(mode). On Windows os.replace does not replace ACLs; chmod may raise OSError for group/other bits.

**Impact:** Transactional rollback can leave files with wrong ACLs after a failed activation, weakening the security promise of atomic installation.

**Likely root cause:** Mode restoration assumes POSIX semantics; no fallback for Windows ACL limitations.

**Suggested remediation:** Best-effort chmod with try/except and owner-only validation on Windows. Full fix requires Windows-specific ACL preservation or a separate ACL snapshot.

---

### HRA-004: Entire test suite assumes POSIX-only capabilities (symlinks, bash, exact modes)

- **Severity:** High
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed. Full suite: 1463 passed, 28 skipped on both branches.

**Evidence:** pytest on Windows initially failed 68+ tests due to: unprivileged symlinks (WinError 1314), missing bash for contract tests, exact POSIX mode assertions, multiprocessing spawn unpickling errors.

**Impact:** Developers on Windows cannot validate changes; CI must run on Linux only, masking Windows-portability bugs in the actual product.

**Likely root cause:** Tests written exclusively for a Linux/Termux target without platform guards.

**Suggested remediation:** Added sys.platform/win32 guards and skip helpers for symlink/permission/bash-dependent tests; relaxed mode assertions to owner-only checks on Windows; documented POSIX-only tests.

---

### HRA-005: Concurrency tests use unpicklable local worker functions

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Skipped on Windows.

**Evidence:** test_m19_a1a3a4a5_real_concurrency.py and siblings define _worker_* as nested functions and call multiprocessing on Windows default 'spawn'.

**Impact:** Tests crash with PicklingError on Windows; cannot verify real concurrency behavior.

**Likely root cause:** Local closures are not picklable; tests assume fork() semantics.

**Suggested remediation:** Skip these tests on Windows where spawn is required; future refactor should move workers to module level or use threading.

---

### HRA-006: Launcher tests attempt to execute shell scripts directly on Windows

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_bootstrap_launcher.py runs the generated launcher via subprocess without a shell interpreter on Windows.

**Impact:** Tests fail because Windows cannot execute a shebang script directly.

**Likely root cause:** Tests assume POSIX shebang execution.

**Suggested remediation:** Use sys.platform guards to run the launcher under bash on Windows, or skip the execute step and verify generated script content instead.

---

### HRA-007: SHA256 bundle digest tests affected by Windows CRLF translation

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_sha256_integrity.py writes shell scripts with write_text(), which on Windows translates newlines to CRLF, altering the hash.

**Impact:** Bundle verification tests fail on Windows and could mask real digest-mismatch bugs in release tooling.

**Likely root cause:** Implicit text-mode newline translation.

**Suggested remediation:** Write test payloads with newline='\n' so hashes are deterministic across platforms.

---

### HRA-008: Canonical-source duplicate scan false-positives on Windows

- **Severity:** Low
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_canonical_source.py uses os.access(X_OK), which always returns True on Windows, flagging every file as an executable entrypoint.

**Impact:** Duplicate-entrypoint regression test fails on Windows with bogus duplicates.

**Likely root cause:** os.access(X_OK) semantics differ on Windows.

**Suggested remediation:** On Windows restrict duplicate scan to .py/.sh script extensions only.

---

### HRA-009: Termux dependency repair test omits gzip and bootstrap from recognized imports

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_termux_dependency_repair.py::test_core_imports_subset_of_runtime fails because code imports gzip and the bootstrap package, neither listed in the test's stdlib/internals sets.

**Impact:** Test incorrectly reports missing runtime requirements, blocking dependency-split validation.

**Likely root cause:** Incomplete stdlib/internals allow-lists in the test.

**Suggested remediation:** Added 'gzip' to stdlib set and 'bootstrap' to internal package set.

---

### HRA-010: API schema freeze test hardcodes /root repo path and uses POSIX grep

- **Severity:** Low
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_m19_api_schema_freeze.py runs 'grep' with cwd='/root/hive-m18/...'.

**Impact:** Test fails on Windows and any checkout not at /root/hive-m18.

**Likely root cause:** Hardcoded absolute path and POSIX-only tool.

**Suggested remediation:** Resolve repo root from __file__ and skip grep-based scan on Windows.

---

### HRA-011: Health-check output test rejects documented error key

- **Severity:** Low
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_m19_health_check_output.py asserts set(result.keys()) <= {'healthy', 'type', 'exit_code'}, but HealthCheck returns an 'error' key when the probe cannot execute.

**Impact:** Correct failure-to-run behavior fails the test.

**Likely root cause:** Test contract does not match implementation's documented error key.

**Suggested remediation:** Allow 'error' in the accepted key set.

---

### HRA-012: Multiple tests assert exact POSIX permission bits on Windows

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_update_cli_workspace.py, test_bootstrap_install_release.py, test_bootstrap_safe_extract.py assert 0o700/0o600 on files and directories.

**Impact:** Tests fail on Windows where ACLs do not map to POSIX group/other bits.

**Likely root cause:** Assumption that chmod() on Windows isolates group/other permissions.

**Suggested remediation:** Check owner read/write/execute only on Windows; keep exact POSIX checks for non-Windows.

---

### HRA-013: Path containment test resolves against real repo root instead of temp dir

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed in test.

**Evidence:** test_m19_malformed_input.py::test_path_traversal_variants_rejected constructs Supervisor but _resolve_path uses module-level _repo_root() derived from __file__, i.e. the real checkout.

**Impact:** Test mutates and validates containment against the live repo directory, not the temp fixture; '....//etc/passwd' resolved to repo_root/etc/passwd.

**Likely root cause:** Supervisor constructor does not accept an injectable repository root; tests did not patch _repo_root.

**Suggested remediation:** Patch _repo_root to temp directory for the duration of the test.

---

### HRA-014: Non-portable '....' path segment misinterpreted by Windows

- **Severity:** Low
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Fixed.

**Evidence:** test_m19_malformed_input.py created a directory named '....'; Windows path normalization collapses it to parent-like behavior.

**Impact:** Test cannot verify that a directory named with dots is not treated as a traversal on Windows.

**Likely root cause:** Windows treats multi-dot-only path segments specially.

**Suggested remediation:** Use 'fourdots' directory name to preserve the same semantics portably.

---

### HRA-015: Restart policy resets attempt counter when window_seconds is zero, allowing infinite crash loops

- **Severity:** High
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** Yes
- **Status:** Fixed in services/restart.py.

**Evidence:** services/restart.py: 'if now - state.first_attempt > self.window_seconds:' resets attempts every call when window_seconds=0, so max_attempts is never exceeded.

**Impact:** A misconfigured or default-zero window can cause a service to restart forever without entering crash-loop protection.

**Likely root cause:** No guard against zero/negative window; comparison '>' with 0 is always true after the first nanosecond.

**Suggested remediation:** Only reset attempts when self.window_seconds > 0.

---

### HRA-016: GitHub Actions not pinned to SHA in CI workflows

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master
- **Blocks V2/RC.2:** No
- **Status:** Open.

**Evidence:** All workflow files use 'uses: actions/checkout@v4' without a commit SHA or version comment. No SHA pinning policy is enforced.

**Impact:** Supply-chain compromise of an action tag would automatically affect builds; reproducibility is weak.

**Likely root cause:** Workflows use floating major-version tags.

**Suggested remediation:** Pin every third-party action to a commit SHA with a '# vX.Y.Z' comment and enable dependabot/renovate for action updates.

---

### HRA-017: Duplicate trust artifact and entrypoint scripts across release/update stores

- **Severity:** Medium
- **Confidence:** High
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Open; documented in duplicate map.

**Evidence:** Duplicate SHA-256: releases/1.0.0/hive-release.pem and updates/trust_store/hive-release.pem are byte-identical. Multiple bin/hive and hive-os scripts exist in bin/, Hive Ops DevAI/bin/, Hive Ops Final/bin/, and Hive Ops Final/original hive os complete/bin/.

**Impact:** Update/trust logic may load stale or wrong artifact; canonical source of truth is unclear; signing-key compromise surface is larger.

**Likely root cause:** Release engineering duplicated artifacts instead of maintaining a single trust_store and a single launcher entrypoint.

**Suggested remediation:** Consolidate to one trust_store/hive-release.pem and one canonical bin/hive launcher; remove legacy Hive Ops */bin duplicates or gate them behind explicit deprecation.

---

### HRA-018: Hardcoded absolute paths in tests and blueprints

- **Severity:** Low
- **Confidence:** Medium
- **Branches:** master, hive-1.1-rc2-bootstrap
- **Blocks V2/RC.2:** No
- **Status:** Partially fixed (test). Blueprints remain.

**Evidence:** Security scan found 498 hardcoded absolute path patterns (Windows drive letters, /root/..., /home/...). Most are in blueprints, docs, and milestone reports. test_m19_api_schema_freeze used /root/hive-m18/... before fix.

**Impact:** Documentation blueprints and some tests assume a fixed filesystem layout, reducing portability and reproducibility.

**Likely root cause:** Milestone reports and blueprints captured host-specific paths from original development environment.

**Suggested remediation:** Audit and replace absolute paths in blueprints/tests with environment-relative or parameterized paths; add a lint rule to block new absolute Windows/Unix paths in source files.

---

## Evidence Index

All raw evidence is under `D:/Hermes-USB-Portable-main/src/TERMUX-RED-TEAM-OPERATING-SYSTEM--audit/evidence/`:

- `master/pytest_initial.txt`, `bootstrap/pytest_initial.txt` — first full-suite failures
- `master/pytest_final.txt`, `bootstrap/pytest_final.txt` — final passing results
- `duplicate_map.json` — SHA-256 duplicate file groups
- `security_scan_raw.json` — raw secret/path-pattern scan hits
- `master/pygount-summary-after-fixes.txt`, `bootstrap/pygount-summary-after-fixes.txt` — language/LOC metrics

## Sign-off

Audit performed on a local Windows host using the portable git toolchain at `D:/Hermes-USB-Portable-main/.cache/runtimes/windows-x64/git/cmd/git.exe`. Both branches were cloned as local worktrees and all fixes were committed locally; no changes were pushed upstream.
