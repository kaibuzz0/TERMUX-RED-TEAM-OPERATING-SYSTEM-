# Milestone 7 Activation and Rollback Design

## State model

STAGED -> VERIFIED -> READY_TO_ACTIVATE -> ACTIVE -> ROLLBACK_AVAILABLE -> ROLLED_BACK

Invalid transitions are rejected by `ActiveState._validate_state_transition()`.

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

## Activation safety gates

- staging verified
- target contained in data_root
- explicit --approve
- transaction lock free or stale-lock recovery approved
- no active pointer schema mismatch
- rollback candidate exists for non-first activation

## Rollback safety gates

- previous release metadata valid
- previous runtime directory exists
- explicit --approve
- failed release preserved
- journal written

## Interruption recovery

Atomic writes use `*.tmp` + `replace()`.
Transaction locks prevent duplicate activation/rollback.
Stale locks can be recovered explicitly.
