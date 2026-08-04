# Phased Implementation Plan

## Milestone 1 — Canonical-source declaration
- Add `canonical.json` metadata.
- Add tests that detect duplicate production entrypoints.
- Preserve all existing user data.
- No runtime reorganization.

## Milestone 2 — Compatibility launcher
- Create canonical `hive` dispatcher.
- Route old `Hive Ops Final/bin/hive*` commands through dispatcher.
- Add command routing tests.

## Milestone 3 — Path and environment repair
- Remove `/root/hive` assumptions.
- Add Termux-aware path resolution.
- Add runtime capability detection.

## Milestone 4 — Authentication correction
- Replace base64 credential storage with hashed vault.
- Rename session gate accurately.
- Add migration and lockout recovery.

## Milestone 5 — Safe installer
- Transaction journal.
- Dry run.
- Local staging.
- Verification.
- Rollback.

## Milestone 6 — Safe updater and repair
- Staged update.
- Verified artifacts.
- Rollback.
- Tiered recovery.

## Milestone 7 — Core state, locking, and logging
- Structured state.
- Locks.
- Bounded audit logging.
- Secret redaction.

## Milestone 8 — Service supervisor
- Managed-process lifecycle.
- Crash-loop controls.
- Android lifecycle handling.

## Milestone 9 — Workspace manager
- Managed contexts.
- Explicit limitation labels.
- PRoot compatibility.

## Milestone 10 — Agent broker and Hermes plugin
- Task schema.
- Permission validation.
- Minimal registered tools.
- Emergency stop.

## Milestone 11 — TUI adaptation
- TUI becomes CLI client.
- No duplicate business logic.

## Milestone 12 — Legacy archive migration
- Move DevAI and legacy subtree to archive.
- Preserve history.
- Add tests preventing runtime imports from archive.
