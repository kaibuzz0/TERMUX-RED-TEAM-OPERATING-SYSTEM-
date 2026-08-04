# Current Permission Model

**Static model.** Actual privilege enforcement is **UNVERIFIED ON TERMUX**.

## Installer permission assumptions

| Script | Assumed identity | Assumed capabilities |
|--------|------------------|----------------------|
| `install-termux.sh` | Normal Termux user | `pkg install`, write `~/`, write `~/.termux/boot`, modify `~/.bashrc` |
| `install.sh` | Normal Termux user | Same as above |
| `update.sh` | Same user as install | Read/write `~/.hive_auth`, `~/.hive_backup`, `~/Hive-Ops`, `~/bin` |
| `emergency-repair.sh` | Same user as install | Delete/recreate `~/Hive-Ops`, modify `~/.bashrc`, boot dir |

## `hive-secure-login` authorization model

- Credentials stored in `~/.hive_auth/passwd`.
- File mode `600` (user read/write only).
- Authentication: compare base64-decoded stored value against entered password+PIN.
- 3-failure lockout with 60-second cooldown.
- Login attempts logged to `~/.hive_auth/login.log`.

## `hive` CLI permission model

- Runs as the Termux user.
- Spawns tmux sessions, shell commands, and Python tools.
- No observed capability-based restrictions (no dedicated seccomp/Landlock wrapper).
- Some paths reference `/root/hive`, which is inaccessible on non-root Termux.

## Agent / orchestrator permission model

- `hive-orchestrator.py` claims recursive agent spawning and self-healing.
- No permission model observed that limits what spawned agents can do.
- Agents can presumably run arbitrary shell commands through the tool scripts.

## Hermes plugin permissions

- `Hermes Plugins/install.sh` copies plugin files into `~/.hermes/plugins/hive-ops-plugin/`.
- Hermes plugins can register hooks/tools/commands; the current skeleton has not been audited for what it actually registers.

## Root vs non-root

- Standard Hive OS scripts do not appear to branch on root status.
- Some scripts use `/root/hive` paths that will fail on non-root devices.
- Root-enhanced capabilities are not separated into a distinct tier.

## Permission gaps

- No separate roles (operator, admin, auditor, release-signer) in current code.
- No short-lived authorization tokens.
- No hardware-token or biometric integration.
- No two-person approval.
