# Milestone 1 — Canonical Source Declaration

## Summary

Created machine-readable and human-readable canonical source declaration.

## Files added

- `hive-canonical.json`
- `docs/CANONICAL_SOURCE.md`
- `tests/test_canonical_source.py`
- `tests/fixtures/canonical-source/known-duplicates.json`

## What was not changed

- No existing production launcher, installer, updater, repair script, authentication system, TUI, gateway, orchestrator, or Hermes integration was modified.
- No source tree was moved or deleted.
- No user data was modified.
- No packages were installed.
- No services were started.
- No network listeners were opened.

## Validation

- 17 stdlib-only tests passed.
- `hive-canonical.json` parses as valid JSON.
- `git diff --check` passed.
- Working tree shows only new untracked files: `blueprints/`, `docs/`, `hive-canonical.json`, `tests/`.

## Hermes self-improvement control

Created `E:/Hermes-USB-Portable-main/config.yaml` with:
```yaml
curator:
  enabled: false
  consolidate: false
```
This disables the automatic curator/skill-maintenance loop during the controlled milestone. No Hermes core file or skill was modified by this milestone.

## Known duplicate entrypoints (migration debt)

- `hive`: `Hive Ops Final/bin/hive` and `Hive Ops Final/original hive os complete/bin/hive`
- `hive-swarm.py`: `Hive Ops DevAI/hive-swarm.py` and `Hive Ops Final/swarm-core/hive-swarm.py`
- `hive_swarm_integration.py`: `Hive Ops DevAI/hive_swarm_integration.py` and `Hive Ops Final/swarm-core/hive_swarm_integration.py`
- `install.sh`: root-level `install.sh` and `Hermes Plugins/install.sh`

These are recorded in `tests/fixtures/canonical-source/known-duplicates.json`. The test `test_no_new_undocumented_duplicates` will fail only if a new undocumented duplicate is added.
