# Data Migration Plan

## User data to preserve

- `~/.hive_auth/` → migrate to vault.
- `~/.hive_ops.txt` → preserve as user notes.
- `~/.hive_backup/` → retain until retention policy expires.
- `~/.hive_rescue/` → review and remove after successful migration.
- `~/.config/hive/` → migrate schema.
- Workspaces in `~/` or `~/.local/share/hive/workspaces/` → preserve.

## Migration steps

1. Inventory existing user data.
2. Create pre-migration backup.
3. Run schema migration (dry-run first).
4. Verify migrated state.
5. Retain old data until operator confirms success.
6. Offer cleanup command.

## No data loss rule

Untracked user files, repositories, and notes must survive migration.
