# File Classification Ledger

**Scope:** all significant files and directories. Classifications are based on static inspection and the canonical-source decision.

| Path | Classification | Evidence | Confidence | Intended future location | Runtime depends on it? | Removal breaks install/update/repair/boot? | Termux verification required? |
|------|----------------|----------|------------|--------------------------|------------------------|--------------------------------------------|------------------------------|
| `install-termux.sh` | CANONICAL (requires rewrite) | Primary installer linked to Final | HIGH | Root-level canonical installer | Yes | Yes — install path | Yes |
| `update.sh` | CANONICAL (requires rewrite) | Primary updater | HIGH | Root-level canonical updater | Yes | Yes — update path | Yes |
| `emergency-repair.sh` | CANONICAL (requires rewrite) | Primary repair | HIGH | Root-level canonical repair | Yes | Yes — repair path | Yes |
| `README.md` | SUPPORTING (requires rewrite) | User-facing docs | HIGH | Root-level docs | No | No | No |
| `requirements.txt` | CANONICAL (requires pin/hashes) | Python deps | HIGH | Root-level canonical deps | Yes (DevAI runtime) | Partial | No |
| `install.sh` | LEGACY | Installs DevAI tree, not maintained by updater/repair | HIGH | `archive/` or delete | No | No | No |
| `Hive Ops Final/bin/hive` | CANONICAL | Unified CLI | HIGH | `core/bin/hive` | Yes | Yes | Yes |
| `Hive Ops Final/bin/hive-ui-v2` | CANONICAL | README-described TUI | HIGH | `core/bin/hive-ui` | Yes | Yes (login flow) | Yes |
| `Hive Ops Final/bin/hive-secure-login` | CANONICAL (requires hash fix) | Boot login | HIGH | `core/bin/hive-auth` or `core/lib/auth.sh` | Yes | Yes | Yes |
| `Hive Ops Final/etc/env.sh` | CANONICAL | Environment setup | HIGH | `core/etc/env.sh` | Yes | Yes | Yes |
| `Hive Ops Final/etc/bash-integration.sh` | CANONICAL (requires rewrite) | `.bashrc` integration | HIGH | `core/etc/shell-integration.sh` | Yes | Yes | Yes |
| `Hive Ops Final/.termux/boot/00-hive-secure.sh` | CANONICAL | Boot script | HIGH | `core/boot/termux-secure-boot.sh` | Yes | Yes | Yes |
| `Hive Ops Final/lib/swarm_bridge.py` | CANONICAL (requires audit) | Swarm bridge | MEDIUM | `core/lib/swarm_bridge.py` | Yes | No | Yes |
| `Hive Ops Final/tools/` | CANONICAL (requires audit) | 27 tools | HIGH | `core/tools/` | No | No | Yes |
| `Hive Ops Final/original hive os complete/` | LEGACY / ARCHIVE | Embedded duplicate legacy tree | HIGH | `archive/original-hive-os-complete/` | No | No | No |
| `Hive Ops DevAI/hive-ctrl.py` | REFERENCE IMPLEMENTATION ONLY | DevAI controller | HIGH | `integrations/devai-legacy/` or merge into core | No | No | No |
| `Hive Ops DevAI/hive-orchestrator.py` | REFERENCE IMPLEMENTATION ONLY | Autonomous orchestrator | HIGH | `archive/` or bounded redesign | No | No | No |
| `Hive Ops DevAI/bin/hivedev-*` | REFERENCE IMPLEMENTATION ONLY / SUPPORTING | Specialist tools | HIGH | Selectively merge into `core/tools/` | No | No | Yes |
| `brain-plug/therapist_code only.py` | EXPERIMENTAL / SUPPORTING | Creative/therapy Flask app | HIGH | `integrations/brain-plug/` or `plugins/brain-plug/` | No | No | Yes |
| `brain-plug/escape_living_ai.txt` | EXPERIMENTAL | Symbolic corpus | HIGH | `integrations/brain-plug/` or archive | No | No | No |
| `Hermes Plugins/hive-ops-plugin/` | EXPERIMENTAL (requires redesign) | Hermes plugin skeleton | MEDIUM | `integrations/hermes/plugin/` | No | No | Yes |
| `.github/workflows/ci.yml` | SUPPORTING (requires SHA pinning) | CI | HIGH | `.github/workflows/ci.yml` | No | No | No |
| `ENTRY` | UNKNOWN | Empty placeholder | HIGH | Investigate or delete | No | No | No |
| `EOF` | UNKNOWN | Empty placeholder | HIGH | Investigate or delete | No | No | No |
