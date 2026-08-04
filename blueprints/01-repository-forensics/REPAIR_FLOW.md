# Repair Flow

## Source Script: `emergency-repair.sh`

**Entry line:** `#!/data/data/com.termux/files/usr/bin/bash`
**Options:** `bash emergency-repair.sh [--full-nuke]`
**Target directory:** `$HOME/Hive-Ops`
**Rescue directory:** `$HOME/.hive_rescue`

### Standard repair flow (no flag)

1. Clear screen, print warning banner.
2. Interactive `ask()` — user must confirm `y`.
3. `mkdir -p "$RESCUE_DIR"`.
4. Preserve `~/.hive_auth` → `$RESCUE_DIR/.hive_auth`.
5. Preserve `~/.hive_ops.txt` → `$RESCUE_DIR/.hive_ops.txt`.
6. Copy `~/.bashrc` → `$RESCUE_DIR/bashrc.backup`.
7. `rm -rf "$INSTALL_DIR"`.
8. `rm -rf "$HOME/bin/hive"*` (unquoted glob).
9. `rm -f "$HOME/.termux/boot/00-hive*"`.
10. `git clone --depth 1` into `$INSTALL_DIR`.
11. Restore credentials and notes from `$RESCUE_DIR`.
12. Re-link `Hive Ops Final/bin/hive*` into `~/bin`.
13. Re-add bash integration line to `~/.bashrc` if missing.
14. Re-copy boot script.

### Full-nuke flow (`--full-nuke`)

1. Print stronger warning and require confirmation.
2. Still preserves `~/.bashrc` backup.
3. `rm -rf "$INSTALL_DIR"`.
4. `rm -rf "$HOME/bin/hive"*`.
5. `rm -f "$HOME/.termux/boot/00-hive*"`.
6. `rm -rf "$HOME/.hive_auth"` and `rm -f "$HOME/.hive_ops.txt"`.
7. Re-clone from GitHub.
8. Prompt the user to enter a new password and PIN, base64-encode them into `~/.hive_auth/passwd`.

## Observations and risks

- Paths are not fully quoted (`$HOME/bin/hive*` without quotes; variable expands into multiple arguments).
- `rm -rf "$INSTALL_DIR"` removes the entire install tree; if `$INSTALL_DIR` is empty/malicious, unintended deletions are possible.
- The `--full-nuke` mode deletes credentials permanently, but the warning string is printed with `err` which exits after the message before `ask` is reached — the actual confirmation prompt still appears because `err` is called inside a string that is printed, but `err()` itself exits. This appears to be a bug: the `err "This will DELETE everything..."` line likely terminates the script before the user can confirm.
- No offline mode; standard repair and nuke both require network.
- Rescue directory is not encrypted and is world-readable by default (umask 077 helps but does not protect rescue files from the same Android app UID).
- No integrity verification of the freshly cloned code.
