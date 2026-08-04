# Hive OS Activation and Rollback

**Milestone 7**

## Activation state model

```
STAGED -> VERIFIED -> READY_TO_ACTIVATE -> ACTIVE -> ROLLBACK_AVAILABLE -> ROLLED_BACK
```

Transitions that are not listed above are rejected by `ActiveState`.

## Requirements for activation

- Staging completed successfully.
- Source manifest verifies against staged files.
- Target runtime path is inside the approved installation root.
- Transaction journal is valid and complete.
- No unresolved conflict remains.
- Activation is explicitly approved (`--approve`).

## Active installation layout

```
$HIVE_DATA_ROOT/
  releases/
    <release-id>/
      runtime/
      .release.json
  active.json
$HIVE_STATE_ROOT/
  install-journal/
  .install-lock
```

`active.json` is a JSON pointer rather than a symlink, because symlink support
cannot be assumed on all target filesystems.

## Rollback

- The previous release must be verified (state `ACTIVE` or `ROLLED_BACK` in metadata).
- The failed release is preserved for forensics.
- A journal entry records the rollback.
- No user data outside the installation root is mutated.

## Interruption recovery

The atomic write pattern (`*.tmp` + `replace`) plus transaction locking means:

- Interrupted before pointer switch: stale lock can be recovered, no active pointer changed.
- Interrupted after pointer switch: active pointer points to the new release; previous release id is preserved.
- Interrupted rollback: lock prevents duplicate rollback; re-run is safe.

## Physical Termux validation plan

See `MILESTONE7_REPORT.md`.
