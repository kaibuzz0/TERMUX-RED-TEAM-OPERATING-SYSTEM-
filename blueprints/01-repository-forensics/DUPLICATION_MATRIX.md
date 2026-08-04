# Duplication Matrix

## High-level duplication groups

### 1. Two parallel Hive CLI implementations

| Aspect | `Hive Ops Final/bin/hive` | `Hive Ops DevAI/bin/hive-os` / `Hive Ops DevAI/hive-ctrl.py` |
|--------|---------------------------|---------------------------------------------------------------|
| Language | Python | Python |
| Commands | `status`, `health`, `net`, `services`, `dashboard`, `swarm`, `speak`, `logs`, `ps`, `doctor`, `audit`, `backup`, `restore` | `status`, `start`, `stop`, `health`, `logs`, `config`, `backup`, `restore`, `update`, `duress`, plus per-component control |
| Network modes | `orbot`, `local`, `off` | Implicit via `hivedev-net`, `hivedev-comms`, etc. |
| TUI | `hive-ui-v2` | `hive-ui` |
| Boot | `hive-secure-login` + `00-hive-secure.sh` | `hive-boot` + `00-hive-devai` |

**Evidence:**
- Path: `Hive Ops Final/bin/hive` lines 10-30 (command list)
- Path: `Hive Ops DevAI/hive-ctrl.py` lines 15-30 (usage help)
- Confidence: HIGH

### 2. Two parallel swarm / orchestrator modules

| File | Location |
|------|----------|
| `swarm_orchestrator.py` | `Hive Ops DevAI/` |
| `hive-orchestrator.py` | `Hive Ops DevAI/` |
| `swarm-core/swarm_orchestrator.py` | `Hive Ops Final/` |
| `swarm-core/hive-swarm.py` | `Hive Ops Final/` |
| `hive_swarm_integration.py` | both top-level `Hive Ops DevAI/` and `Hive Ops Final/swarm-core/` |

**Evidence:**
- Inventory paths.
- Confidence: CONFIRMED

### 3. Duplicate `brain-plug/escape_living_ai.txt` and `therapist_code only.py` history

Git log shows commits:
- `50b0bc5 Remove duplicate therapist_code only.py (exists in root brain-plug/)`
- `2ab2bb6 Remove duplicate escape_living_ai.txt (exists in root brain-plug/)`

This indicates earlier duplicates existed and were removed; the canonical copies are now under `brain-plug/`.

### 4. Legacy subtree inside canonical tree

| Path | Content |
|------|---------|
| `Hive Ops Final/original hive os complete/` | Full older Hive OS tree including `bin/hive`, `etc/dev.aliases.sh`, `hive_bootstrap.sh`, `.termux/boot/00-hive.sh` |

This is an embedded historical copy of the project inside the current "Final" tree.

### 5. Boot scripts

| Path | Purpose |
|------|---------|
| `Hive Ops Final/.termux/boot/00-hive-ops.sh` | Legacy ops boot |
| `Hive Ops Final/.termux/boot/00-hive-secure.sh` | Secure-login boot |
| `Hive Ops Final/original hive os complete/.termux/boot/00-hive.sh` | Older boot script |
| `Hive Ops DevAI/bin/hive-boot` | DevAI boot entry |

### 6. Environment files

| Path | Purpose |
|------|---------|
| `Hive Ops Final/etc/env.sh` | Sets HIVE_HOME, PATH, etc. |
| `Hive Ops Final/original hive os complete/.config/hive/env.sh` | Older env file |
| `install.sh` generated `~/.config/hive/env.sh` | Runtime env file |

### 7. Shell integration

| Path | Purpose |
|------|---------|
| `Hive Ops Final/etc/bash-integration.sh` | `.bashrc` integration + banner |
| `Hive Ops Final/shell/.bashrc` | Example `.bashrc` |
| `Hive Ops Final/original hive os complete/etc/dev.aliases.sh` | Legacy aliases |

## Recommended disposition

- **Resolve dual CLI** by choosing one canonical CLI (`hive`) and converting the other into either a compatibility alias or archive.
- **Merge or archive duplicate swarm/orchestrator files** into a single module under the canonical tree.
- **Remove `original hive os complete/`** from the active canonical tree; move to `archive/`.
- **Consolidate boot scripts** into one per supported profile.
- **Consolidate env/alias files** into `etc/`.
