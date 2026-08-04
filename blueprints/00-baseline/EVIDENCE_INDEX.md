# Evidence Index

## Guardrail event

- **Date/time:** Current session
- **Tool:** `read_file` / `search_files` / `terminal`
- **Error:** `Git Bash not found. Hermes Agent requires Git for Windows on Windows. ...`
- **Recovery method:** Switched to `execute_code` with Python `pathlib`/`subprocess` using the bundled Git binary at `E:/Hermes-USB-Portable-main/.cache/runtimes/windows-x64/git/cmd/git.exe`. Added `safe.directory` exception for the new clone.
- **Recorded in:** This file and the Phase 0 completion report.

## Repository baseline evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| Remote is `kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-` | `.git/config` `origin` URL from `git remote -v` | CONFIRMED |
| Branch is `master`, HEAD `1b7e10a` | `git rev-parse HEAD`, `git branch --show-current` | CONFIRMED |
| Tag `v1.0.0` exists | `git tag --list` | CONFIRMED |
| Working tree clean except `blueprints/` | `git status --short` | CONFIRMED |
| No submodules | `git submodule status` | CONFIRMED |
| No worktrees besides default | `git worktree list` | CONFIRMED |

## File inventory evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| 155 files in repo | `blueprints/00-baseline/raw_inventory.json` | CONFIRMED |
| `Hive Ops Final/` = 84 files | Inventory count by top-level dir | CONFIRMED |
| `Hive Ops DevAI/` = 54 files | Inventory count by top-level dir | CONFIRMED |
| 25 `.sh` files, 48 `.py` files | Inventory extension counts | CONFIRMED |
| Root scripts are `install-termux.sh`, `install.sh`, `update.sh`, `emergency-repair.sh` | Inventory + head reads | CONFIRMED |

## Architecture evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| Two parallel CLI trees exist (`Hive Ops Final/bin/hive` and `Hive Ops DevAI/bin/hive-os`/`hive-ctrl.py`) | Head reads of both command lists | HIGH |
| `install-termux.sh` links only `Hive Ops Final/bin/hive*` | Full read of `install-termux.sh` | CONFIRMED |
| `install.sh` links only `Hive Ops DevAI/bin/hive*`/`hivedev*` | Head read of `install.sh` | HIGH |
| Credentials stored base64-encoded, not encrypted | Full read of `install-termux.sh` `setup_credentials()` | CONFIRMED |
| `update.sh` can stash local changes in `--force` mode | Full read of `update.sh` | CONFIRMED |
| `emergency-repair.sh` has `--full-nuke` mode | Full read of `emergency-repair.sh` | CONFIRMED |
| Hermes plugin skeleton exists | Head read of `Hermes Plugins/install.sh` | HIGH |
| CI workflow lints `Hive Ops DevAI`, runs bandit, builds tarball | Full read of `.github/workflows/ci.yml` | CONFIRMED |

## Security evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| Multiple `curl ... | bash` / `wget ... | sh` references in README and installer docs | Static regex scan | HIGH |
| Multiple `rm -rf` occurrences | Static regex scan | HIGH |
| `git reset --hard`, `git clean`, `git stash` in `update.sh` | Full read | CONFIRMED |
| Public-listener patterns found in some files | Static regex scan | MEDIUM |
| `eval` and `source <(...)` found | Static regex scan | MEDIUM |
| Base64 credential storage | Full read of `install-termux.sh` | CONFIRMED |

## Skill modification evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| `termux-mobile-ops/SKILL.md` contains a "Windows Portable Environment Fallbacks" section not in the 2026-07-31 13:35:20 backup | `difflib` comparison | CONFIRMED |
| Modification predates current session | mtime `1785801452.0` (year 2026+ Unix timestamp) | HIGH |

## Evidence files generated in this session

- `blueprints/00-baseline/REPOSITORY_BASELINE.md`
- `blueprints/00-baseline/ENVIRONMENT_BASELINE.md`
- `blueprints/00-baseline/raw_inventory.json`
- `blueprints/00-baseline/head_inspection_dump.md`
- `blueprints/01-repository-forensics/COMPLETE_FILE_INVENTORY.md`
- `blueprints/01-repository-forensics/DIRECTORY_PURPOSE_MAP.md`
- `blueprints/01-repository-forensics/ENTRYPOINT_MAP.md`
- `blueprints/01-repository-forensics/COMMAND_MAP.md`
- `blueprints/01-repository-forensics/INSTALLATION_FLOW.md`
- `blueprints/01-repository-forensics/UPDATE_FLOW.md`
- `blueprints/01-repository-forensics/REPAIR_FLOW.md`
- `blueprints/01-repository-forensics/HERMES_INTEGRATION_MAP.md`
- `blueprints/01-repository-forensics/DUPLICATION_MATRIX.md`
- `blueprints/01-repository-forensics/UNKNOWN_COMPONENTS.md`
- `blueprints/03-security/SECURITY_RISK_REGISTER.md`
