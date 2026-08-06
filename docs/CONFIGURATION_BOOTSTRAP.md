# Configuration Bootstrap Layer

The bootstrap layer provides the minimal information required before the Configuration Engine can locate and load its own files.

## Purpose

The bootstrap layer is **not** a second configuration system. It only resolves:

- repository root
- configuration root
- state root
- log root
- selected profile
- portable/runtime mode indicators

All other configuration is obtained through `config_engine` after initialization.

## Allowed bootstrap inputs

| Input | Source | Validation |
| ----- | ------ | ---------- |
| `HIVE_REPO_ROOT` | environment | must be absolute path containing `hive-canonical.json` |
| `HIVE_CONFIG_ROOT` | environment | must be absolute path |
| `HIVE_STATE_ROOT` | environment | must be absolute path |
| `HIVE_LOG_ROOT` | environment | must be absolute path |
| `HIVE_PROFILE` | environment | must be a valid profile name |
| `HOME` / `USERPROFILE` | environment | fallback for default roots |
| `hive-canonical.json` | repository root file | schema_version + required keys |

## Bootstrap layer constraints

- Cannot define arbitrary subsystem settings.
- Cannot bypass schema validation.
- Cannot inject plugin paths or executable code.
- Cannot enable experimental or mutating features.
- All values are validated before use.

## Bootstrap implementation

The bootstrap layer lives in:

- `lib/hive_path.py` — repository root and filesystem root resolution
- `config_engine/config.py` — profile selection and root assembly
- `config_engine/environment.py` — allow-listed environment override extraction

## Rejection of bootstrap abuse

Attempts to use bootstrap inputs for non-bootstrap purposes are classified as configuration debt and must be migrated to the engine.
