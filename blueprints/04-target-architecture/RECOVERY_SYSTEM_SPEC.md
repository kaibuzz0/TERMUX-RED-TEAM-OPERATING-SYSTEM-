# Recovery System Specification

## Recovery levels

| Level | Name | Purpose |
|-------|------|---------|
| 0 | Diagnose | Inspect state, locks, logs, integrity |
| 1 | Repair links/permissions | Fix symlinks, PATH, generated state |
| 2 | Restore canonical runtime from local verified copy | Use staged/verified runtime prefix |
| 3 | Roll back last update | Re-point active runtime symlink |
| 4 | Reinstall runtime while preserving config/data | Fresh verified archive, keep `~/.config/hive` and vault |
| 5 | Restore encrypted recovery bundle | Offline bundle with operator passphrase |
| 6 | Explicit destructive reset | Delete all Hive state after typed confirmation |

## Level definitions

### Level 0 — Diagnose

- Preconditions: operator has shell access.
- Files changed: none (read-only).
- Internet: not required.
- Approval: none.
- Output: diagnostic report.

### Level 1 — Repair links/permissions

- Preconditions: diagnose completed.
- Files changed: symlinks, permissions, generated state.
- Files preserved: all user data.
- Internet: not required.
- Approval: `--yes` or interactive.
- Verification: `hive verify`.

### Level 2 — Restore canonical runtime from local verified copy

- Preconditions: staged/verified runtime exists.
- Files changed: active runtime pointer.
- Files preserved: config, vault, state, backups.
- Internet: not required.
- Approval: interactive.
- Verification: hash check + health check.

### Level 3 — Roll back last update

- Preconditions: previous runtime prefix exists.
- Files changed: active runtime symlink.
- Files preserved: config, vault, state.
- Internet: not required.
- Approval: interactive.
- Verification: health check.

### Level 4 — Reinstall runtime while preserving config/data

- Preconditions: verified archive or network available.
- Files changed: runtime prefix.
- Files preserved: `~/.config/hive/`, vault, state, backups, user data.
- Internet: optional (offline bundle preferred).
- Approval: interactive.
- Verification: hash check + health check.

### Level 5 — Restore encrypted recovery bundle

- Preconditions: recovery bundle exists, operator has passphrase.
- Files changed: runtime, config, state as dictated by bundle.
- Files preserved: user data not included in bundle.
- Internet: not required.
- Approval: interactive + passphrase.
- Verification: bundle signature/digest.

### Level 6 — Explicit destructive reset

- Preconditions: operator explicitly requests reset.
- Files changed: delete Hive state directories.
- Files preserved: nothing by default (operator may opt to preserve specific exports).
- Internet: not required.
- Approval:
  - Display exact target paths.
  - Require typed confirmation phrase (e.g., `DELETE-HIVE-DATA`).
  - Validate that target paths are within expected Hive data dirs.
  - Validate root-boundary (do not touch `/root/`, `/data/`, other apps).
  - Offer backup first.
  - No misleading `err()` label.
  - No recursive deletion of an unvalidated variable.

## Failure behavior

- Every level has a rollback to the previous level.
- If a level fails, state is left as-is unless explicitly rolled back.
- All recovery actions are logged.
