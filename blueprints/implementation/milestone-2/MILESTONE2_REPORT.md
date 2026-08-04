# Milestone 2 — Compatibility Launcher and Canonical Command Routing

## Summary

Introduced the repository-level canonical launcher `bin/hive` that routes to the declared canonical internal launcher `Hive Ops Final/bin/hive`.

## Files added

- `bin/hive` — repository-level compatibility launcher.
- `docs/COMPATIBILITY_LAUNCHERS.md` — launcher policy and duplicate-entrypoint inventory.
- `tests/test_compatibility_launcher.py` — launcher tests.

## Files updated

- `hive-canonical.json` — added `current_canonical_launcher` and updated `migration_state`.
- `docs/CANONICAL_SOURCE.md` — documented the launcher relationship.
- `tests/test_canonical_source.py` — added launcher-related assertions.
- `tests/fixtures/canonical-source/known-duplicates.json` — added `bin/hive` as a known duplicate (new wrapper vs internal canonical launcher).

## What was not changed

- No production tree was moved or deleted.
- No existing launcher, installer, updater, repair, authentication, TUI, gateway, orchestrator, or Hermes integration was rewritten.
- No packages installed, no services started, no listeners opened.

## Design decisions

- Python chosen for the launcher so it can be statically tested on Windows and uses `sys.executable` to invoke the canonical launcher, avoiding shebang/executable-bit assumptions.
- `--resolve` diagnostic performs validation and exits 1 on invalid metadata.
- Launcher refuses to route to any path outside `current_canonical_source` (so DevAI cannot become a fallback).
