# ADR-0005: Storage Layout

## Status

Proposed.

## Context

Hive OS needs a predictable, profile-aware storage layout that respects Termux app-private storage.

## Decision

```text
~/.config/hive/          # configuration
~/.local/share/hive/     # runtime state, logs, backups, workspaces, vault
~/storage/               # Android shared storage (explicit exports only)
```

Active runtime is a symlink under `~/.local/share/hive/active/`. Versioned runtimes live under `~/.local/share/hive/runtimes/<version>/`.

## Consequences

- Easy rollback by re-pointing symlink.
- App-private data is protected by Android.
- Shared storage is opt-in.

## Rejected alternatives

- `/root/hive` — fails on non-root Termux.
- Scattered state in `~/.hive_*` — hard to manage and back up.
