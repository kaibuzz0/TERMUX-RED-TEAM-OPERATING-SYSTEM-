# Current Failure Modes

**Static model.** Actual failure behavior is **UNVERIFIED ON TERMUX**.

## Installation failures

| Failure | Consequence | Recovery |
|---------|-------------|----------|
| `pkg install` fails mid-list | Partial package set; scripts may fail at runtime | Rerun installer; no transactional rollback |
| `git clone` fails | No install directory | Retry installer; requires network |
| `~/.bashrc` append fails | No auto-banner/aliases | Manual source line repair |
| Credential prompt interrupted | Missing `~/.hive_auth/passwd`; login fails | Rerun `hive-secure-login` or installer |

## Boot/login failures

| Failure | Consequence | Recovery |
|---------|-------------|----------|
| `~/.hive_auth/passwd` missing | Login cannot authenticate | Rerun installer or nuke mode |
| Wrong password/PIN 3 times | 60-second lockout | Wait or delete lock file |
| `hive-secure-login` exits | User returns to shell without UI | Manual launch |
| Another Termux session opened | Bypasses login prompt entirely | No enforcement; redesign required |

## Update failures

| Failure | Consequence | Recovery |
|---------|-------------|----------|
| `git pull` fails after backup | Backup exists, code unchanged | Manual restore from `~/.hive_backup/` |
| `--force` stashes local changes | Uncommitted work lost | Git stash may be recoverable |
| Re-link misses `~/.local/bin` DevAI links | DevAI commands stale | Rerun `install.sh` or manual relink |
| Backup restore fails | Credentials/config lost | Use earlier `~/.hive_backup/` entry |

## Repair failures

| Failure | Consequence | Recovery |
|---------|-------------|----------|
| `--full-nuke` exits before confirm (suspected bug) | Nuke not performed | Script must be fixed before use |
| `rm -rf` path expands unexpectedly due to unquoted glob | Possible data loss | Avoid running until fixed |
| `git clone` fails during repair | No working code | Requires network; no offline path |
| Rescue directory left behind | Credentials readable in `~/.hive_rescue/` | Delete after successful repair |

## Runtime failures

| Failure | Consequence | Recovery |
|---------|-------------|----------|
| `/root/hive` path used on non-root Termux | Permission denied | Redesign paths to use `$HOME` |
| `tmux` not installed | `hive start` fails | Install tmux |
| Orbot not installed/running | Tor routing fails | Start Orbot or use `local` mode |
| Agent orchestrator recursion unbounded | Resource exhaustion | Kill processes; redesign bounds |
| Plugin fails to load | Hermes integration unavailable | Debug plugin registration |

## Security-relevant failure modes

| Failure | Consequence |
|---------|-------------|
| Base64 credential file leaked | Password+PIN recoverable |
| Update server compromised | Malicious code installed automatically |
| Repair deletes wrong directory | Data loss |
| Listener bound to `0.0.0.0` | Remote exposure on untrusted networks |
| Agent executes unbounded commands | Privilege escalation / data exfiltration |
