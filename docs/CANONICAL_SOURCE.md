# Hive OS Canonical Source Declaration

**Milestone 1 — Canonical Source Declaration**

This document declares the present and future source structure of Hive OS. It is a metadata milestone; it does not reorganize the repository, move any source tree, or change runtime behavior.

## Current canonical source

**`Hive Ops Final/`**

## Current canonical launcher

**`Hive Ops Final/bin/hive`**

This is the executable that handles Hive subcommands today. Milestone 2 introduces a thin repository-level compatibility launcher (`bin/hive`) that delegates to this path.

This directory is the present canonical production source for Hive OS. It is the tree referenced by the existing `install-termux.sh` and `update.sh` installers and by the existing root-level command wrappers.

It is classified as **CANONICAL AFTER LIMITED REPAIR** because the current code contains security and maintainability issues (e.g., base64 credential storage, unverified remote execution paths, hardcoded `/root/hive` references) that must be repaired before it can serve as the long-term canonical runtime.

## Future target runtime tree

**`core/`**

This is the planned canonical runtime tree. It does not yet exist. The current routing uses `Hive Ops Final/bin/hive` as the active internal launcher.

`core/` is the planned future canonical runtime tree. It does not yet exist. It will be introduced incrementally across later milestones, starting with the canonical `hive` dispatcher in Milestone 2. Until `core/` is established and validated, `Hive Ops Final/` remains the active canonical source.

## Reference implementation

**`Hive Ops DevAI/`**

`Hive Ops DevAI/` is a reference implementation and experimental tree. It contains additional agent/orchestrator ideas that are not yet integrated into the canonical installers or repair flow. It remains in place for study and selective porting. It is **not** the canonical source and must not be installed as the production runtime.

## Root-level compatibility entrypoints

The root-level scripts (`install-termux.sh`, `install.sh`, `update.sh`, `emergency-repair.sh`) remain compatibility entrypoints during the migration. They are not replaced in this milestone. Future milestones will introduce staged, verified replacements while preserving these scripts as a fallback during the deprecation period.

## What this milestone does not change

- No directory is moved, renamed, or deleted.
- No existing launcher is rewritten.
- No installer, updater, repair system, authentication system, TUI, gateway, orchestrator, or Hermes integration is modified.
- No package is installed.
- No runtime behavior changes.
- No user data is modified.

## Future milestones

- **Milestone 2** (current) introduces the repository-level `bin/hive` compatibility launcher. It delegates to `Hive Ops Final/bin/hive` and preserves all existing launchers.
- **Milestone 12** may move `Hive Ops DevAI/` and legacy subtrees to `archive/` once all references are resolved and tests prevent runtime imports from archive paths.

## Runtime validation

All runtime behavior remains **UNVERIFIED ON TERMUX** until tested on a physical Android device. This declaration is a static repository fact, not a runtime claim.
