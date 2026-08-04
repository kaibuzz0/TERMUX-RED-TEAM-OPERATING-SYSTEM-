# Hive OS Path Model

**Milestone 4 — Scoped Canonical Runtime Path Repair**

## Path categories

| Category | Description | Example default on Termux |
|----------|-------------|---------------------------|
| `REPOSITORY_ROOT` | Bundled source and assets from the checked-out repository. | `/data/data/com.termux/files/home/TERMUX-RED-TEAM-OPERATING-SYSTEM-` |
| `CANONICAL_SOURCE_ROOT` | The current canonical production tree. | `<REPOSITORY_ROOT>/Hive Ops Final` |
| `CONFIG_ROOT` | User-controlled Hive configuration. | `$HOME/.config/hive` |
| `STATE_ROOT` | Mutable runtime state. | `$HOME/.local/state/hive` |
| `DATA_ROOT` | Persistent Hive-owned application data. | `$HOME/.local/share/hive` |
| `CACHE_ROOT` | Disposable caches. | `$HOME/.cache/hive` |
| `LOG_ROOT` | Bounded logs. | `$STATE_ROOT/logs` |
| `TEMP_ROOT` | Validated temporary files. | `$TMPDIR/hive` |
| `BIN_ROOT` | Canonical executable locations. | `<CANONICAL_SOURCE_ROOT>/bin` |
| `LEGACY_INSTALL_ROOT` | Historical `/root/hive` compatibility path. | `/root/hive` (legacy only) |

## Path authority

`lib/hive_path.py` is the single source of truth for path resolution. It provides:

- `resolve_repository_root()`
- `resolve_canonical_source()`
- `resolve_canonical_launcher()`
- `resolve_config_root()`
- `resolve_state_root()`
- `resolve_data_root()`
- `resolve_cache_root()`
- `resolve_log_root()`
- `resolve_temp_root()`
- `resolve_legacy_root()`

## Environment overrides (narrow allowlist)

| Variable | Affects |
|----------|---------|
| `HIVE_HOME` | Legacy install root; also used by `env.sh` and some derived paths |
| `HIVE_CONFIG_ROOT` | Configuration root |
| `HIVE_STATE_ROOT` | Mutable state root |
| `HIVE_DATA_ROOT` | Persistent data root |
| `HIVE_CACHE_ROOT` | Cache root |
| `HIVE_LOG_ROOT` | Log root |
| `HIVE_TEMP_ROOT` | Temporary root |
| `HIVE_OS_ROOT` | Legacy OS data root replacement |
| `HIVE_SWARM_ROOT` | Legacy swarm data root replacement |

All overrides must be absolute paths. Relative paths are rejected.

## Legacy compatibility

`/root/hive` is treated as a legacy installation path. The current canonical launcher no longer requires it. If a future migration needs to read legacy state, it must:

1. Check for explicit operator override.
2. Check standard user-state defaults.
3. Only then check legacy path, and only if it exists.
4. Never create `/root/hive`.

## Files repaired in Milestone 4

- `Hive Ops Final/bin/hive` — derives roots from environment variables and `lib/hive_path.py`, removes `/root/hive` default
- `Hive Ops Final/etc/env.sh` — removes `/root/hive-os` and `/root/hive-swarm` defaults
- `Hive Ops Final/etc/services.json` — replaces absolute `/root/...` paths with `${HIVE_*}` token references

## Files deferred

- `Hive Ops Final/bin/hive-dashboard` — reachable but not part of core startup/status/doctor; listener presence requires separate review
- `Hive Ops Final/tools/` and `Hive Ops Final/swarm-core/` — excluded from this milestone
