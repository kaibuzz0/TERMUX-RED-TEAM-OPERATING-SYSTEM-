# Deprecated / reference launchers

Files in this directory are historical entrypoints moved here during the
HIVE OS FINAL PRODUCTION canonical-runtime consolidation (REM-009).

They are **not** shipped in production release payloads and are **not**
executed by the modern bootstrap or updater. They are preserved for audit
continuity and reference only.

## Current canonical entrypoints

- `bin/hive` — authoritative production dispatcher
- `bin/hive-os` — compatibility wrapper that delegates to `bin/hive`

## Historical copies

- `Hive Ops Final/bin/hive`
- `Hive Ops Final/original hive os complete/bin/hive`
- `Hive Ops DevAI/bin/hive-os`
