# Hive OS Service Model

**Milestone 5 — Service Loader Validation and Structured Path Expansion**

## Current service loader

The active service loader in `Hive Ops Final` is the legacy bash script:

```text
Hive Ops Final/original hive os complete/bin/hive_services.sh
```

It reads `.svc` files under `$HIVE_ETC/services/` and executes `nohup bash -lc "$START"`. It does **not** consume `Hive Ops Final/etc/services.json`.

## New services.json schema

`Hive Ops Final/etc/services.json` has been migrated to schema version 2 with structured command objects. Example:

```json
{
  "name": "hive-daemon",
  "start": {
    "interpreter": "python",
    "base": "canonical-source",
    "path": "bin/hive",
    "args": ["start"]
  },
  "log": {
    "base": "log-root",
    "path": "supervisor.log"
  },
  "requires": ["tmux"],
  "auto_start": true
}
```

## Allowed path bases

| Base | Resolves to |
|------|-------------|
| `repository` | repository root |
| `canonical-source` | `Hive Ops Final/` |
| `config-root` | `$HIVE_CONFIG_ROOT` or `$HOME/.config/hive` |
| `state-root` | `$HIVE_STATE_ROOT` or `$HOME/.local/state/hive` |
| `data-root` | `$HIVE_DATA_ROOT` or `$HOME/.local/share/hive` |
| `cache-root` | `$HIVE_CACHE_ROOT` or `$HOME/.cache/hive` |
| `log-root` | `$HIVE_LOG_ROOT` or `$STATE_ROOT/logs` |
| `temp-root` | `$HIVE_TEMP_ROOT` or `$TMPDIR/hive` |

## Command execution model

- Commands are argument arrays, not shell strings.
- `shell=False`.
- Interpreter is explicitly selected: `python`, `bash`, or `sh`.
- Scripts must be relative to an approved base.
- Arguments are preserved as separate tokens.

## Legacy compatibility

- Schema version 1 string commands are still parsed by `lib/hive_service_loader.py` for backward compatibility.
- Legacy strings are flagged as deprecated but accepted if they contain only allowed `${VAR}` tokens and no shell metacharacters.
- Unknown schema versions fail closed.

## Validation command

```text
hive --validate-services-json
```

This command:
- Parses `services.json`.
- Resolves all paths.
- Validates command safety.
- Reports errors and warnings.
- Does not start any service.
- Does not create directories.
- Does not open listeners.
