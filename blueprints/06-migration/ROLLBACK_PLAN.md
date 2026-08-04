# Rollback Plan

## Rollback levels

- **Runtime rollback:** re-point active runtime symlink to previous version.
- **Config rollback:** restore from `~/.local/share/hive/backups/config/`.
- **State rollback:** restore from `~/.local/share/hive/backups/state/`.
- **Data rollback:** restore from full backup.

## Triggers

- Health check failure after update.
- Operator invokes `hive update rollback`.
- Recovery tool detects corruption.

## Procedure

1. Verify rollback target exists and is valid.
2. Acquire recovery lock.
3. Backup current state.
4. Re-point active runtime.
5. Restore config/state if needed.
6. Run health check.
7. Log rollback event.
8. Release lock.

## Fallback

If automatic rollback fails, operator uses `hive recovery` levels.
