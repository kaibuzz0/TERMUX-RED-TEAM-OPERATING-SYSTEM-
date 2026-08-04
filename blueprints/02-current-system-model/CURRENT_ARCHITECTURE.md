# Current Architecture

**Scope:** the repository as it exists at HEAD `1b7e10a`. All runtime claims are labeled **UNVERIFIED ON TERMUX**.

## 1. Root-level installation entry points

| File | Role | Status |
|------|------|--------|
| `install-termux.sh` | One-line Termux installer; installs into `~/Hive-Ops`, links `Hive Ops Final/bin/hive*`, copies secure-login boot script, base64-codes credentials | DOCUMENTED + IMPLEMENTED statically |
| `install.sh` | Legacy unified installer; installs into `~/hive`, links `Hive Ops DevAI/bin/*`, sets Hermes env vars | DOCUMENTED + IMPLEMENTED statically |
| `update.sh` | GitHub-pull updater for `~/Hive-Ops`; backs up `~/.hive_auth`, `~/.hive_ops.txt`, `~/.bashrc` | DOCUMENTED + IMPLEMENTED statically |
| `emergency-repair.sh` | Re-clone / nuke repair script | DOCUMENTED + IMPLEMENTED statically |
| `requirements.txt` | Python dependencies (loose lower bounds) | DOCUMENTED + IMPLEMENTED |
| `README.md` | Install/update/repair/user docs | DOCUMENTED |

## 2. `Hive Ops Final/`

| Area | Components | Status |
|------|------------|--------|
| `bin/` | `hive` (unified Python CLI), `hive-ui-v2` (ANSI TUI), `hive-secure-login` (bash login), `hive-dashboard`, `hive-legacy` | IMPLEMENTED statically |
| `etc/` | `env.sh`, `bash-integration.sh`, `services.json` | IMPLEMENTED statically |
| `.termux/boot/` | `00-hive-ops.sh`, `00-hive-secure.sh` | IMPLEMENTED statically |
| `lib/` | `swarm_bridge.py` | IMPLEMENTED statically |
| `tools/` | 27 standalone security/research scripts | IMPLEMENTED statically |
| `swarm-core/` | `hive-swarm.py`, `swarm_orchestrator.py`, `swarm_pet.py`, integration/state files | IMPLEMENTED statically |
| `shell/` | `.bashrc`, `.zshrc`, `notes.txt` | DOCUMENTED |
| `original hive os complete/` | Embedded legacy tree | LEGACY |

## 3. `Hive Ops DevAI/`

| Area | Components | Status |
|------|------------|--------|
| `bin/` | 45+ `hive-*`/`hivedev-*` specialist scripts | IMPLEMENTED statically |
| top-level Python | `hive-ctrl.py`, `hive-orchestrator.py`, `hive-gateway.py`, `hive-swarm.py`, `hive_agents.py`, `swarm_orchestrator.py`, `swarm_pet.py`, `hive_swarm_integration.py` | IMPLEMENTED statically |
| `lib/` | `stealth.py` | IMPLEMENTED statically |
| `docs/` | `THREAT_MATRIX.md` | DOCUMENTED |

## 4. `Hermes Plugins/`

| Path | Role | Status |
|------|------|--------|
| `install.sh` | Copies skeleton into `~/.hermes/plugins/hive-ops-plugin/` | IMPLEMENTED statically |
| `hive-ops-plugin/__init__.py` | Plugin registration stub | IMPLEMENTED statically, REACHABILITY UNVERIFIED |
| `hive-ops-plugin/brain_plug.py` | Brain-Plug adapter | IMPLEMENTED statically, REACHABILITY UNVERIFIED |
| `hive-ops-plugin/agents/__init__.py` | Agent package stub | IMPLEMENTED statically |

## 5. `brain-plug/`

| Path | Role | Status |
|------|------|--------|
| `therapist_code only.py` | Flask-based NLP/lyrics/therapy/numerology tool | IMPLEMENTED statically |
| `escape_living_ai.txt` | Symbolic/ritual text corpus | DOCUMENTED |
| `README.md` | Creative/therapy module docs | DOCUMENTED |

## 6. Runtime integration points (inferred, **UNVERIFIED ON TERMUX**)

```text
Termux boot
    ~/.termux/boot/00-hive-secure.sh
        hive-secure-login
            ~/.hive_auth/passwd (base64 password+PIN)
            on success → hive-ui-v2
                hive <subcommand>
                    Hive Ops Final/bin/hive-legacy  OR  Python logic  OR  swarm_bridge.py

Shell init
    ~/.bashrc
        source "~/Hive Ops Final/etc/bash-integration.sh"
            source env.sh, banner, aliases

Manual install
    install-termux.sh
        pkg install ...
        git clone
        ln -s "~/Hive-Ops/Hive Ops Final/bin/hive*" ~/bin/
        cp 00-hive-secure.sh ~/.termux/boot/
        create ~/.hive_auth/passwd
        append .bashrc source line

Update
    update.sh
        backup ~/.hive_auth, ~/.hive_ops.txt, ~/.bashrc
        git pull
        restore
        re-link
        re-copy boot script

Repair
    emergency-repair.sh
        preserve credentials
        rm -rf ~/Hive-Ops
        git clone
        restore + re-link
```

## 7. Network listeners

Static scan found `http.server`, `Flask`, `FastAPI`, and `0.0.0.0` / listener-related strings in some files. Whether any of these actually bind a port in normal operation is **UNVERIFIED ON TERMUX**.

## 8. External downloads

| Source | Path | Purpose | Verification |
|--------|------|---------|--------------|
| GitHub raw `install-termux.sh` | README curl example | Install | NONE (curl \| bash) |
| GitHub raw `update.sh` | README curl example | Update | NONE |
| GitHub repo clone/pull | `install-termux.sh`, `update.sh`, `emergency-repair.sh` | Install/update/repair | NONE beyond TLS |

## 9. State directories and files (runtime targets)

| Path | Purpose | Host sensitivity |
|------|---------|------------------|
| `~/.hive_auth/passwd` | Base64 password+PIN | HIGH |
| `~/.hive_ops.txt` | User notes | MEDIUM |
| `~/.hive_backup/<ts>/` | Update backups | MEDIUM |
| `~/.hive_rescue/` | Repair rescue files | MEDIUM |
| `~/.config/hive/env.sh` | Environment config | MEDIUM |
| `~/.hermes/plugins/hive-ops-plugin/` | Hermes plugin runtime copy | MEDIUM |
| `~/Hive-Ops/` | Install directory | LOW |
| `~/hive/` | Legacy install directory | LOW |
| `~/bin/hive*` | Symlinks to Final binaries | LOW |
| `~/.local/bin/hive*`/`hivedev*` | Symlinks to DevAI binaries | LOW |
| `~/.termux/boot/00-hive-secure.sh` | Boot script | MEDIUM |

## 10. No single canonical source

`Hive Ops Final/` and `Hive Ops DevAI/` are parallel production trees. The choice is documented separately in `blueprints/06-migration/CANONICAL_SOURCE_DECISION.md`.
