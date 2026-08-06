# Hive OS Configuration Engine

The `config_engine/` package is the single authority for all Hive OS configuration.

## Principle

No subsystem reads configuration files directly. Every subsystem obtains configuration through:

```python
from config_engine import get_config
config = get_config("services")
```

## Architecture

- `schema.py` — typed subsystem schemas and validation
- `loader.py` — safe JSON/YAML file loading
- `validator.py` — cross-field and security validation
- `merger.py` — layer merging and variable substitution
- `profiles.py` — profile inheritance
- `transactions.py` — atomic commit/rollback lifecycle
- `migration.py` — schema migration engine
- `defaults.py` — built-in schemas and profiles
- `environment.py` — allowed environment overrides
- `persistence.py` — atomic filesystem storage
- `audit.py` — audit logging
- `preview.py` — dry-run output
- `cli.py` — `hive config *` commands
- `errors.py` — typed errors

## Configuration layers

1. Hive defaults
2. Platform defaults
3. Profile
4. User configuration files
5. Environment overrides
6. Runtime overrides

## Built-in profiles

- `default`
- `minimal`
- `development`
- `portable`
- `production`
- `termux`
- `desktop-linux`
- `windows`

## CLI

```bash
hive config show
hive config validate
hive config preview
hive config profiles
hive config profile NAME
hive config schema
hive config history
hive config rollback
```
