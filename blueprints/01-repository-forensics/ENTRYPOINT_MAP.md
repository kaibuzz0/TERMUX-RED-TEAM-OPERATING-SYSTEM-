# Entrypoint Map

**Observation basis:** filenames, shebangs, and first-200-line inspection. No dynamic execution.

## Root-Level Entry Points

| Entry Point | Type | Implements | Launched By |
|-------------|------|------------|-------------|
| `install-termux.sh` | bash | Termux one-line install/update path | User / README / curl pipe |
| `install.sh` | bash | Legacy unified installer | User / README |
| `update.sh` | bash | GitHub-pull update with credential backup | User / README |
| `emergency-repair.sh` | bash | Re-clone / nuke recovery | User / README |
| `requirements.txt` | pip manifest | Python dependencies | `pip install -r` |
| `README.md` | docs | Install/update/repair instructions | User reads |

## `Hive Ops Final/bin/` Entry Points

| Command | File | Type | Purpose |
|---------|------|------|---------|
| `hive` | `Hive Ops Final/bin/hive` | Python | Unified CLI controller (status, health, net, services, dashboard, swarm, speak, logs, ps, doctor, audit, backup, restore) |
| `hive-ui-v2` | `Hive Ops Final/bin/hive-ui-v2` | Python | Full-screen ANSI TUI menu |
| `hive-secure-login` | `Hive Ops Final/bin/hive-secure-login` | bash | Password+PIN login prompt, launches `hive-ui-v2` |
| `hive-dashboard` | `Hive Ops Final/bin/hive-dashboard` | shell | ASCII TUI dashboard (legacy UI) |
| `hive-legacy` | `Hive Ops Final/bin/hive-legacy` | shell | Fallback to bash scripts |

## `Hive Ops DevAI/bin/` Entry Points (representative, 45+ scripts)

| Command Prefix | Count | Purpose |
|----------------|-------|---------|
| `hivedev-*` | ~40 | Specialist security/operations tools (anomaly, av, backup, clipboard, comms, container, duress, emf, exfil, firewall, forensics, gateway, geo, hide, honey, inject, integrity, intel, key, log, mem, net, node, pet, pq, secureboot, shred, spoof, swarm, temporal, vault, volume, etc.) |
| `hive-os` | 1 | DevAI CLI entry |
| `hive-42` | 1 | "Ultimate Question" easter egg / meta entry |
| `hive-boot` | 1 | Boot orchestration |
| `hive-hermes` | 1 | Hermes bridge |
| `hive-ui` | 1 | Legacy UI |
| `hivedev` | 1 | Top-level hivedev dispatcher |
| `hivedev-alias` | 1 | Alias manager |
| `hivedev-anchor` | 1 | Anchor/persistence tool |

## `Hive Ops DevAI/` Top-Level Python Modules

| Module | Purpose |
|--------|---------|
| `hive-ctrl.py` | Unified controller for all DevAI components |
| `hive-orchestrator.py` | Autonomous recursive agent swarm orchestrator |
| `hive-gateway.py` | Gateway bridge |
| `hive-swarm.py` | Swarm CLI |
| `hive_agents.py` | Agent framework classes |
| `hive_swarm_integration.py` | Swarm integration glue |
| `swarm_orchestrator.py` | Standalone swarm orchestrator |
| `swarm_pet.py` | Swarm "pet" companion |

## `Hive Ops Final/` Subsystem Entry Points

| Path | Purpose |
|------|---------|
| `Hive Ops Final/etc/env.sh` | Environment variables (HIVE_HOME, PATH, etc.) |
| `Hive Ops Final/etc/bash-integration.sh` | `.bashrc` integration + banner |
| `Hive Ops Final/.termux/boot/00-hive-ops.sh` | Termux:Boot startup (legacy ops) |
| `Hive Ops Final/.termux/boot/00-hive-secure.sh` | Termux:Boot startup with secure login |
| `Hive Ops Final/lib/swarm_bridge.py` | Python bridge to swarm |
| `Hive Ops Final/tools/` | 27 stand-alone security/research scripts |

## `brain-plug/` Entry Points

| Path | Purpose |
|------|---------|
| `brain-plug/therapist_code only.py` | Flask API for lyrics/therapy/numerology |
| `brain-plug/escape_living_ai.txt` | Symbolic/ritual text corpus |

## `Hermes Plugins/` Entry Points

| Path | Purpose |
|------|---------|
| `Hermes Plugins/install.sh` | Copies plugin skeleton into `~/.hermes/plugins/hive-ops-plugin/` |
| `Hermes Plugins/hive-ops-plugin/__init__.py` | Plugin registration stub |
| `Hermes Plugins/hive-ops-plugin/brain_plug.py` | Brain-Plug adapter |

## Boot / Shell Init Chain (inferred)

```text
Termux:Boot fires ~/.termux/boot/00-hive-secure.sh
    └── hive-secure-login
            └── on success, launches hive-ui-v2
.bashrc
    └── source "~/Hive Ops Final/etc/bash-integration.sh"
            └── source env.sh, display banner, register aliases
hive / hive-os / hive-ctrl
    └── dispatch to component scripts or Python modules
```

## Call Graph (high-level)

```text
User
  install-termux.sh
    pkg install ...
    git clone REPO
    ln -s "Hive Ops Final/bin/hive*" ~/bin/
    cp "Hive Ops Final/.termux/boot/00-hive-secure.sh" ~/.termux/boot/
    base64 credentials -> ~/.hive_auth/passwd

User
  ~/.termux/boot/00-hive-secure.sh
    hive-secure-login
      ~/.hive_auth/passwd
      hive-ui-v2
        hive <subcommand>
          "Hive Ops Final/bin/hive-legacy" OR Python logic OR swarm_bridge.py

User
  update.sh
    git pull
    relink "Hive Ops Final/bin/hive*"

User
  emergency-repair.sh
    rm -rf ~/Hive-Ops
    git clone
    relink
```
