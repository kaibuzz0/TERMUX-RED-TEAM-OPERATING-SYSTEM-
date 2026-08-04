# Hive OS Compatibility Launcher Policy

**Milestone 2 — Compatibility Launcher and Canonical Command Routing**

## Canonical repository entrypoint

The repository-level canonical entrypoint is:

```text
bin/hive
```

All new scripts and external integrations should invoke this path. It is a thin compatibility launcher that reads `hive-canonical.json` and forwards arguments to the current canonical internal launcher.

## Current internal canonical launcher

```text
Hive Ops Final/bin/hive
```

This is the existing Python launcher that implements Hive subcommands today. The compatibility launcher does not reimplement its logic.

## Known duplicate/legacy launchers

| Base name | Paths | Classification | Notes |
|-----------|-------|----------------|-------|
| `hive` | `Hive Ops Final/bin/hive` | CURRENT CANONICAL | Routed to by `bin/hive` |
| `hive` | `Hive Ops Final/original hive os complete/bin/hive` | LEGACY | Unmaintained duplicate; migration debt |
| `hive` | `bin/hive` (new) | COMPATIBILITY WRAPPER | Repository-level canonical entrypoint |
| `hive-os` | `Hive Ops DevAI/bin/hive-os` | REFERENCE | DevAI only; never production fallback |
| `hive-ctrl.py` | `Hive Ops DevAI/hive-ctrl.py` | REFERENCE | DevAI only |
| `hive-hermes` | `Hive Ops DevAI/bin/hive-hermes` | REFERENCE | DevAI only |
| `hive-orchestrator.py` | `Hive Ops DevAI/hive-orchestrator.py` | REFERENCE | DevAI only |
| `hive-swarm.py` | `Hive Ops DevAI/hive-swarm.py`, `Hive Ops Final/swarm-core/hive-swarm.py` | DUPLICATE | Migration debt |
| `hive_swarm_integration.py` | `Hive Ops DevAI/hive_swarm_integration.py`, `Hive Ops Final/swarm-core/hive_swarm_integration.py` | DUPLICATE | Migration debt |
| `install.sh` | root-level `install.sh`, `Hermes Plugins/install.sh` | DUPLICATE | Migration debt |
| `hive-ui-v2` | `Hive Ops Final/bin/hive-ui-v2` | CURRENT CANONICAL | TUI launcher |
| `hive-secure-login` | `Hive Ops Final/bin/hive-secure-login` | CURRENT CANONICAL | Session gate launcher |

## Operational launchers

The following launchers remain operational during Milestone 2 and are **not** removed:

- `Hive Ops Final/bin/hive`
- `Hive Ops Final/bin/hive-ui-v2`
- `Hive Ops Final/bin/hive-secure-login`
- Root-level `install-termux.sh`, `install.sh`, `update.sh`, `emergency-repair.sh`

## Non-fallback rule

`Hive Ops DevAI/` is **never** used as a fallback production path. The compatibility launcher validates that the resolved canonical launcher resides inside `current_canonical_source` (`Hive Ops Final`). If the metadata ever pointed to a DevAI path, the launcher would reject it.

## Future milestones

- **Milestone 3+**: gradually introduce `core/bin/hive` and a compatibility layer that routes old command names to the new dispatcher.
- **Milestone 12**: move legacy/DevAI subtrees to `archive/` once all references are resolved and tests prevent runtime imports from archive paths.

## Path safety

- The launcher derives paths from its own location.
- It rejects paths escaping the repository.
- It rejects paths outside the canonical source tree.
- It does not modify `PATH`, `.bashrc`, or global configuration.
- It does not install packages or download code.
- It forwards arguments unchanged and preserves exit codes.

## Runtime qualification

Launcher behavior is statically verified on Windows. Actual Termux execution (chmod, shebang, argument/exit-code forwarding, spaces in paths) remains **UNVERIFIED ON TERMUX** until tested on a physical Android device.


## Milestone 4 — Scoped path repair

The repository-level launcher now invokes the canonical launcher with `sys.executable` because the canonical target is a Python script. The canonical launcher itself now uses `lib/hive_path.py` to resolve roots and removes `/root/hive` from its active default path.

Supported path overrides:

- `HIVE_HOME` — legacy data root
- `HIVE_OS_ROOT` — OS data root
- `HIVE_SWARM_ROOT` — swarm data root
- `HIVE_CONFIG_ROOT` — configuration root
- `HIVE_STATE_ROOT` — mutable state root
- `HIVE_DATA_ROOT` — persistent data root
- `HIVE_CACHE_ROOT` — cache root
- `HIVE_LOG_ROOT` — log root
- `HIVE_TEMP_ROOT` — temporary root

All overrides must be absolute paths.
