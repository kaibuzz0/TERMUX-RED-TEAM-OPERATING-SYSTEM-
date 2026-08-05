# HIVE OS Credential Flow Map

**Milestone 8 Audit**

This document maps credential-related code paths without including actual secret values.

## Active credential paths

### `Hive Ops Final/bin/hive-secure-login` (session gate)

- **Component**: operator session gate / secure login terminal
- **Credential type**: password + 4-digit PIN
- **Storage format**: base64-encoded plaintext in `$HOME/.hive_auth/passwd`
- **Creation flow**: `_setup_auth()` prompts for password/PIN, writes `printf ''%s\n%s' "$PASS1" "$PIN1" | base64 > "$AUTH_FILE"`
- **Verification flow**: `_check_auth()` decodes base64 and compares strings directly
- **Permissions**: `chmod 700 "$AUTH_DIR"`, `chmod 600 "$AUTH_FILE"`
- **Log exposure**: login.log records SUCCESS/FAIL/LOCKOUT but not the secret values
- **Environment exposure**: none
- **Subprocess exposure**: none direct; password read via `read -rs`
- **Recovery behavior**: emergency-repair.sh preserves `.hive_auth` in rescue dir and restores it
- **Bypass possibilities**: base64 is trivially reversible; anyone with file read access obtains password+PIN
- **Status**: **active, legacy, high risk**

### `Hive Ops Final/.termux/boot/00-hive-secure.sh` (boot launcher)

- **Component**: Termux:Boot integration
- **Credential type**: none stored; delegates to `hive-secure-login`
- **Storage format**: none
- **Status**: **active, no direct credential storage**

### `emergency-repair.sh` (recovery script)

- **Component**: emergency repair / reinstallation
- **Credential type**: `.hive_auth` directory contents
- **Storage format**: copied as-is (preserves base64 file)
- **Creation flow**: copies `$HOME/.hive_auth` to `$RESCUE_DIR` and restores
- **Log exposure**: logs rescue operations but not credential contents
- **Status**: **legacy, preserves weak storage**

### `update.sh` (update script)

- **Component**: update framework
- **Credential type**: `.hive_auth` directory contents
- **Storage format**: copied as-is to timestamped backup
- **Creation flow**: `cp -r "$HOME/.hive_auth" "$BACKUP_DIR/"`
- **Log exposure**: logs backup path but not contents
- **Status**: **legacy, preserves weak storage**

### Environment / `.env` references

- **Component**: various modules reference `.env` for configuration
- **Credential type**: potential API keys/tokens
- **Status**: **unknown, under review; no concrete plaintext secret found in production runtime**

## Reachability classification

| Path | Status |
|------|--------|
| `Hive Ops Final/bin/hive-secure-login` | active / legacy |
| `emergency-repair.sh` credential copy | active / legacy |
| `update.sh` credential backup | active / legacy |
| `.env` references | unknown / review |
| `auth.json` references | not found in current tree (legacy detection target) |

## Key finding

The only active credential storage is `$HOME/.hive_auth/passwd` in the `hive-secure-login` script, and it stores the operator password+PIN as base64-encoded plaintext. This is the primary target for Milestone 8 vault migration.
