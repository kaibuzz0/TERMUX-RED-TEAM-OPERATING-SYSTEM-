# Current Process Model

**Static model.** Actual process behavior is **UNVERIFIED ON TERMUX**.

## Operator-facing processes

| Process | Trigger | Lifetime | Children | Notes |
|---------|---------|----------|----------|-------|
| `bash install-termux.sh` | User / README curl | One-shot | `pkg`, `git`, `ln`, `cp` | Modifies `~/.bashrc`, `~/.termux/boot`, `~/.hive_auth` |
| `bash update.sh` | User | One-shot | `git`, `cp`, `ln` | Backs up and restores credentials |
| `bash emergency-repair.sh` | User | One-shot | `rm`, `git`, `cp`, `ln` | Re-clones or nukes |
| `~/.termux/boot/00-hive-secure.sh` | Android/Termux:Boot | Short-lived parent | `hive-secure-login` | Boot wrapper |
| `hive-secure-login` | Boot wrapper | Until auth success/fail | `hive-ui-v2` on success | Interactive bash script |
| `hive-ui-v2` | Login success | Session TUI | `hive` subcommands | ANSI menu |
| `hive` | User/TUI | Per-subcommand | `hive-legacy`, tmux, Python tools | Unified CLI |

## Background / daemon-like processes

| Process | Source | Claimed behavior | Status |
|---------|--------|------------------|--------|
| `hive start` tmux session | `Hive Ops Final/bin/hive` | Manages a tmux session named `hive` | UNVERIFIED |
| Tor / Orbot proxy | `hive net orbot|local` | Routes network through Tor | UNVERIFIED |
| Swarm agents | `Hive Ops DevAI/hive-orchestrator.py` | Recursive agent spawning, self-healing | UNVERIFIED |
| Brain-Plug Flask | `brain-plug/therapist_code only.py` | HTTP API on `/api` endpoints | UNVERIFIED |

## Agent / orchestrator process model (from source comments)

```text
Master Orchestrator (hive-orchestrator.py)
    ├── Domain Controllers
    │     ├── security
    │     ├── crypto
    │     ├── network
    │     └── ...
    ├── Task Executors
    │     └── specific operations
    └── Verification Agents
```

**Observations:**
- The orchestrator code advertises recursive agent spawning without human intervention.
- This is a high-risk pattern for runaway delegation and must be bounded in the target architecture.

## Lifecycle model

```text
Installation
    → Boot
        → Login
            → TUI
                → Command dispatch
    → Update (periodic)
        → Backup → Pull → Restore → Relink
    → Repair (on failure)
        → Preserve → Wipe → Re-clone → Restore → Relink
```

## No supervisor observed

There is no evidence of a dedicated watchdog/supervisor process that monitors and restarts Hive components. `Hive Ops Final/bin/hive_watchdog.sh` exists in the legacy subtree but is not referenced by the current install flow.
