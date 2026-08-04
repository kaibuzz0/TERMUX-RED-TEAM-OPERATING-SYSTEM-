# Command Map

**Scope:** Commands explicitly documented or implemented in the root README and `Hive Ops Final/bin/hive`. Commands from `Hive Ops DevAI/bin/hivedev-*` are too numerous to fully map without runtime inspection; below are representative groups.

## `hive` Unified CLI (`Hive Ops Final/bin/hive`)

| Subcommand | Purpose | Notes |
|------------|---------|-------|
| `hive status` | Full system status (OS + swarm + network) | |
| `hive health` | Health check; exit 0 if green | |
| `hive start` / `hive stop` | Manage tmux session | |
| `hive net {orbot|local|off|newnym|status|test}` | Network control | Default `orbot` on 127.0.0.1:9050; `local` uses bundled Tor on :9052; `off` is fail-closed |
| `hive services {list|start|stop|status|health}` | Service management | Reads `Hive Ops Final/etc/services.json` |
| `hive dashboard` | Launch TUI | ASCII dashboard |
| `hive swarm {status|init}` | Swarm operations | |
| `hive speak` | Brain-Plug handshake | |
| `hive logs` | Tail logs | |
| `hive ps` | Process status | |
| `hive doctor` | Environment audit | |
| `hive audit` | Full system audit | |
| `hive backup` / `hive restore` | Backup operations | |

## Shell Aliases (from `Hive Ops Final/etc/bash-integration.sh` / README)

| Alias | Expansion |
|-------|-----------|
| `hh` | `hive health` |
| `hs` | `hive status` |
| `hd` | `hive dashboard` |
| `hn` | `hive net status` |
| `hsv` | `hive services status` |
| `hlog` | `hive logs` |
| `hps` | `hive ps` |

## `Hive Ops DevAI/bin/` Representative Command Groups

| Group | Commands |
|-------|----------|
| Security / defense evasion | `hivedev-hide`, `hivedev-spoof`, `hivedev-av`, `hivedev-duress`, `hivedev-secureboot`, `hivedev-shred` |
| Network | `hivedev-net`, `hivedev-comms`, `hivedev-comms3`, `hivedev-gateway`, `hivedev-node`, `hivedev-firewall` |
| Forensics / intel | `hivedev-forensics`, `hivedev-intel`, `hivedev-log`, `hivedev-mem`, `hivedev-geo` |
| Persistence / vault | `hivedev-vault`, `hivedev-key`, `hivedev-backup`, `hivedev-clipboard`, `hivedev-volume` |
| Swarm / agents | `hivedev-swarm`, `hivedev-swarm-integration`, `hivedev-swarm-manager`, `hivedev-pet`, `hivedev-anomaly`, `hivedev-pq`, `hivedev-temporal` |
| Injection / analysis | `hivedev-inject`, `hivedev-honey`, `hivedev-emf`, `hivedev-container` |
| Utility | `hivedev-alias`, `hivedev-anchor`, `hive-42`, `hive-boot`, `hive-os`, `hive-hermes`, `hive-ui` |

## Installer / Updater / Repair Commands

| Command | Behavior |
|---------|----------|
| `bash install-termux.sh` | Install into `~/Hive-Ops`, link `Hive Ops Final/bin/hive*`, copy boot script, base64 credentials |
| `bash install.sh` | Legacy install into `~/hive`, link `Hive Ops DevAI/bin/*` |
| `bash update.sh [--force]` | Backup `~/.hive_auth`, `~/.hive_ops.txt`, `~/.bashrc`; `git fetch`/`pull`; restore; relink |
| `bash emergency-repair.sh [--full-nuke]` | Re-clone; preserve credentials by default; nuke deletes credentials |

## Command Conflicts

- `hive-ui` (DevAI) vs `hive-ui-v2` (Final) — two different TUI implementations.
- `hive-os` (DevAI) vs `hive` (Final) — two different unified CLI entry points.
- `install.sh` vs `install-termux.sh` — target different install directories and binary sets.
- Both `Hive Ops Final/` and `Hive Ops DevAI/` contain swarm/orchestrator code with similar names (`swarm_orchestrator.py`, `hive-orchestrator.py`).
