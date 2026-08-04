# Shell Safety Audit

## Scope

All `.sh` files and bash shebangs in the repository.

## Key scripts audited

| Script | Shell | `set` flags | Notable safety issues |
|--------|-------|-------------|------------------------|
| `install-termux.sh` | Termux bash | `-euo pipefail`, `umask 077` | Uses `clear`; appends to `~/.bashrc`; base64 credentials |
| `install.sh` | bash | `-e` | Broader package install; sets env vars; less strict error handling |
| `update.sh` | Termux bash | `-euo pipefail`, `umask 077` | `--force` stashes silently; unverified remote pull |
| `emergency-repair.sh` | Termux bash | `-uo pipefail`, `umask 077` | **No `-e`**, unquoted globs, suspected `--full-nuke` exit bug |
| `Hive Ops Final/bin/hive-secure-login` | bash | `-euo pipefail`, `umask 077` | Base64 comparison; lockout file |
| `Hive Ops Final/.termux/boot/00-hive-ops.sh` | bash | not inspected fully | Boot script |
| `Hive Ops Final/.termux/boot/00-hive-secure.sh` | bash | not inspected fully | Secure boot script |
| `Hive Ops Final/etc/bash-integration.sh` | bash | not inspected fully | Modifies terminal with `tput` |
| `Hermes Plugins/install.sh` | bash | `-e` | Copies files into `~/.hermes/plugins/` |

## Specific findings

### F1 — `emergency-repair.sh` lacks `set -e`

Script uses `set -uo pipefail` but not `-e`. Individual `err()` calls exit, but non-err failures continue.

### F2 — Unquoted globs

```bash
rm -rf "$HOME/bin/hive"*
rm -f "$HOME/.termux/boot/00-hive*"
```

If `$HOME` contains spaces or if the glob expands unexpectedly, unintended files may be deleted.

### F3 — Possible `--full-nuke` control-flow bug

```bash
if [ "$NUKE" -eq 1 ]; then
    warn "FULL NUKE MODE ENABLED"
    err "This will DELETE everything including your login credentials!"
    ask "Are you absolutely sure you want to ERASE all Hive data?"
fi
```

`err()` likely calls `exit 1` after printing. If so, `ask()` is never reached. The destructive nuke path may either (a) exit before confirmation or (b) require the user to run again without confirming, depending on `err()` implementation. The `--full-nuke` flag is therefore **UNSAFE AS WRITTEN** and must be validated on Termux before use.

### F4 — `rm -rf "$INSTALL_DIR"`

`$INSTALL_DIR` is set to `$HOME/Hive-Ops`. No validation that the variable is non-empty and under `$HOME` before removal.

### F5 — README recommends `curl ... | bash`

Two one-liners in README execute remote scripts directly. This trains users to run remote code without inspection.

### F6 — `update.sh --force` stashes local changes

```bash
if [ "$FORCE" -eq 1 ]; then
    warn "Force mode: stashing local changes..."
    git stash || true
fi
```

User modifications are stashed silently; recovery requires the user to know git stash.

### F7 — Path construction in `install-termux.sh`

Symlink loop:
```bash
for bin in "$INSTALL_DIR/Hive Ops Final/bin"/hive*; do
```

Directory name contains a space; quoting is correct here, but downstream uses like `ln -sf "$bin" "$HOME/bin/$name"` rely on variables being quoted.

### F8 — `install.sh` writes to `~/.bashrc` without idempotency check shown in head

Head inspection of `install.sh` did not show the bashrc integration; full file needs verification.

## Required remediation

1. Always `set -euo pipefail` in safety-critical scripts; remove `err()` ambiguity.
2. Quote every variable and glob; avoid unquoted `*` expansions.
3. Validate paths before `rm -rf` (non-empty, under expected parent, no symlink trickery).
4. Replace `curl | bash` instructions with staged download + verify + execute.
5. Do not silently stash user changes; require explicit action.
6. Fix `--full-nuke` confirmation flow so it always asks before destructive actions.
7. Use `read -r` consistently and avoid word-splitting.
