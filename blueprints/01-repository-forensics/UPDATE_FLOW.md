# Update Flow

## Source Script: `update.sh`

**Entry line:** `#!/data/data/com.termux/files/usr/bin/bash`
**Options:** `bash update.sh [--force]`
**Target directory:** `$HOME/Hive-Ops`
**Backup directory:** `$HOME/.hive_backup/<YYYYMMDD_HHMMSS>`

### Step-by-step flow

1. Parse `--force` flag; if set, `FORCE=1`.
2. Verify `$HOME/Hive-Ops/.git` exists; error if not.
3. `mkdir -p "$BACKUP_DIR"`.
4. Copy `~/.hive_auth` → backup.
5. Copy `~/.hive_ops.txt` → backup if exists.
6. Copy `~/.bashrc` → backup.
7. `cd "$INSTALL_DIR"`.
8. If `FORCE=1`, `git stash || true`.
9. `git fetch origin master`.
10. Compare `LOCAL=$(git rev-parse HEAD)` and `REMOTE=$(git rev-parse origin/master)`.
11. If equal, exit 0 ("Already up to date").
12. `git pull origin master`.
13. Restore `~/.hive_auth` from backup, `chmod 700/600`.
14. Restore `~/.hive_ops.txt` if present.
15. Re-link `Hive Ops Final/bin/hive*` into `~/bin`.
16. Re-copy boot script from `Hive Ops Final/.termux/boot/00-hive-secure.sh` to `~/.termux/boot/`.

## Observations and risks

- `--force` stashes local user changes without prompting, which can hide uncommitted work.
- Backups are timestamped but not rotated or verified.
- No rollback path is retained automatically; previous code state is overwritten by `git pull`.
- If `git pull` fails after backup, the system is left in an inconsistent state (backup exists, code unchanged).
- Downloads and executes remote code via `git pull`; no signature or hash verification.
- Does not migrate config schema changes.
- Re-links only `Hive Ops Final/bin/hive*`; if `install.sh` was used, `~/.local/bin` DevAI symlinks are not refreshed.
