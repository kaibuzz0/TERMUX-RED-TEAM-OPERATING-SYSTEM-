# Threat Model

**Scope:** Hive OS as installed by `install-termux.sh` / `install.sh` and operated in standard Termux. Runtime assumptions are labeled.

## Protected assets

| Asset | Sensitivity | Storage location |
|-------|-------------|------------------|
| Hive login password+PIN | HIGH | `~/.hive_auth/passwd` (base64) |
| Hermes configuration / API keys | HIGH | `~/.hermes/.env`, `~/.hermes/config.yaml` |
| Hermes memories and sessions | HIGH | `~/.hermes/memory/`, session DB |
| SSH keys / cloud credentials | HIGH | User-managed paths, potentially imported into Hive |
| User repositories | HIGH | `~/`, `~/storage/` |
| Hive configuration | MEDIUM | `~/.config/hive/`, `~/Hive-Ops/.../etc/` |
| Agent task records | MEDIUM | Runtime-generated logs/state |
| Backups | MEDIUM | `~/.hive_backup/`, `~/.hive_rescue/` |
| Update state | MEDIUM | `~/Hive-Ops/.git/`, `~/.hive_backup/` |
| Operator identity | HIGH | Authentication credentials, logs |
| Security logs | MEDIUM | `~/.hive_auth/login.log`, install/update logs |
| Android shared-storage exports | MEDIUM | `~/storage/` when Termux storage permission granted |

## Threat actors

| Actor | Capability | Relevance |
|-------|------------|-----------|
| Malicious Termux package | Runs inside Termux UID | Medium — if package list is poisoned |
| Compromised upstream (GitHub/PyPI/Termux repo) | Substitutes code | High — no pinning/verification |
| Malicious repository / attacker-controlled repo | Social engineering | Medium |
| Hostile downloaded file | Executes in user space | Medium — tools analyze unknown files |
| Untrusted AI-generated command | Executed via agent | High — orchestrator claims autonomy |
| Runaway Hermes agent | Recursive delegation | High — `hive-orchestrator.py` advertises recursion |
| Another process under Termux UID | Reads `~/.hive_auth` | High — no UID isolation |
| Local person with unlocked device | Bypasses login | High — login is session-only |
| Local person with locked device | Cannot access | Low |
| Remote attacker reaching exposed listener | Network exploitation | Medium — static scan found listener patterns |
| Malicious/compromised update source | Pushes bad code | High — direct pull from GitHub |
| Operator error | Destructive commands | Medium — repair script can delete data |

## Threat scenarios

### T1 — Credential disclosure

- **Asset:** `~/.hive_auth/passwd`
- **Entry point:** any process under Termux UID
- **Weakness:** base64 encoding, not encryption; file readable within same UID
- **Impact:** full impersonation to Hive session lock
- **Current control:** chmod 600
- **Required mitigation:** hash with salt and work factor; do not store plaintext PIN

### T2 — Malicious update

- **Asset:** `~/Hive-Ops/` code
- **Entry point:** `update.sh` / `install-termux.sh` / `emergency-repair.sh`
- **Weakness:** downloads from GitHub with no verification beyond TLS
- **Impact:** arbitrary code execution
- **Current control:** TLS
- **Required mitigation:** signed releases, pinned commits, TUF-style metadata, rollback path

### T3 — Shell injection via installer/update/repair

- **Asset:** Termux shell environment
- **Entry point:** unquoted variables, user-controlled paths
- **Weakness:** `rm -rf "$HOME/bin/hive"*`, unquoted globs
- **Impact:** data loss or unintended command execution
- **Required mitigation:** quote all variables, validate paths, avoid `rm -rf` on user dirs

### T4 — Agent permission escalation

- **Asset:** all user data and credentials
- **Entry point:** `hive-orchestrator.py` recursive spawning
- **Weakness:** no bounds on agent depth, tools, or paths
- **Impact:** runaway execution, data exfiltration
- **Required mitigation:** bounded delegation, explicit allowed paths, toolset restrictions, human approval for destructive ops

### T5 — Public listener exposure

- **Asset:** device network surface
- **Entry point:** Flask/FastAPI/`http.server` in tools
- **Weakness:** possible default `0.0.0.0` binding
- **Impact:** remote access to device services
- **Current control:** unknown
- **Required mitigation:** loopback-only defaults, explicit opt-in for remote bind

### T6 — Boot/login lockout

- **Asset:** operator access
- **Entry point:** corrupted `~/.hive_auth/passwd`, broken boot script
- **Weakness:** login is session-only; broken boot script can make Termux unusable
- **Impact:** denial of access to Termux
- **Required mitigation:** safe mode bypass, boot script validation, offline recovery

### T7 — Backup/rescue leakage

- **Asset:** credentials in `~/.hive_backup/`, `~/.hive_rescue/`
- **Entry point:** any process under Termux UID
- **Weakness:** backup dirs not encrypted
- **Impact:** credential exposure
- **Required mitigation:** encrypt backups, bound retention, verify integrity

### T8 — Supply-chain substitution of Python deps

- **Asset:** runtime behavior
- **Entry point:** `requirements.txt` / `pip install`
- **Weakness:** loose lower-bound pins (no upper bounds, no hashes)
- **Impact:** compromised PyPI package changes behavior
- **Required mitigation:** pinned hashes, hermetic build, reproducible lock file

### T9 — False claims of isolation

- **Asset:** user trust
- **Entry point:** README/marketing text
- **Weakness:** "secure login", "boot authentication", "AI↔AI Security System" suggest stronger guarantees than Termux can provide
- **Impact:** operator over-trusts system
- **Required mitigation:** accurate terminology, explicit Termux limitations

## Risk summary

| Threat | Impact | Likelihood | Risk |
|--------|--------|------------|------|
| T1 Credential disclosure | High | High | HIGH |
| T2 Malicious update | High | Medium | HIGH |
| T4 Agent escalation | High | Medium | HIGH |
| T8 Supply-chain substitution | High | Medium | HIGH |
| T3 Shell injection | Medium | Medium | MEDIUM |
| T5 Public listener | Medium | Low | MEDIUM |
| T6 Boot/login lockout | Medium | Low | MEDIUM |
| T7 Backup leakage | Medium | Medium | MEDIUM |
| T9 False isolation claims | Low | High | MEDIUM |
