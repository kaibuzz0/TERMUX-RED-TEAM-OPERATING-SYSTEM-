# Configuration Authority Audit

This audit documents all direct configuration access in production code after Milestone 14.

## Scope

Production directories scanned:

- `bin/`
- `config_engine/`
- `hive_broker/`
- `installer/`
- `lib/`
- `operations_center/`
- `security/`
- `services/`
- `updates/`

Excluded:

- `tests/`
- `docs/`
- `blueprints/`
- legacy `Hive Ops DevAI/` and `Hive Ops Final/` trees
- `Hermes Plugins/`

## Classification key

- **MIGRATED** — now reads through `config_engine`
- **BOOTSTRAP_EXCEPTION** — required before the engine can initialize
- **LEGACY_COMPATIBILITY** — old code preserved for compatibility, documented debt
- **TEST_ONLY** — not production
- **DOCUMENTATION** — not executable
- **UNMIGRATED** — direct configuration access that should be migrated
- **UNSAFE** — direct access with security concern

## Findings

### 1. `config_engine/config.py`

- `os.environ.get("HOME")` / `os.environ.get("USERPROFILE")` — **BOOTSTRAP_EXCEPTION**. Used only to determine default home before config resolution.
- `os.environ.get("HIVE_REPO_ROOT")` — **BOOTSTRAP_EXCEPTION**. Used to locate the repository before the engine can load.
- `os.environ.get("HIVE_PROFILE")` — **BOOTSTRAP_EXCEPTION**. Selects the active profile before config resolution.

These reads are the narrow bootstrap surface and are validated before use.

### 2. `config_engine/loader.py`

- `yaml.safe_load(f)` — **MIGRATED**. Used only inside the Configuration Engine for user configuration files.

### 3. `lib/hive_path.py`

- `os.environ.get("HIVE_REPO_ROOT")` — **BOOTSTRAP_EXCEPTION**.
- `os.environ.get("HOME")` for default roots — **BOOTSTRAP_EXCEPTION / LEGACY_COMPATIBILITY**.
- `load_metadata()` reads `hive-canonical.json` — **BOOTSTRAP_EXCEPTION**. Repository identity metadata is not user configuration.
- `resolve_*_root()` family — **BOOTSTRAP_EXCEPTION / LEGACY_COMPATIBILITY**. These helpers provide fallback defaults while subsystems migrate to `config_engine`.

Decision: `lib/hive_path.py` becomes the explicit bootstrap path layer. It is not a second configuration authority; it only resolves filesystem roots.

### 4. `lib/hive_runtime.py`

- `os.environ.get("HOME")`, `os.environ.get("PREFIX")`, `os.environ.get("TMPDIR")`, `os.environ.get("TEMP")`, `os.environ.get("TERMUX_VERSION")`, etc. — **BOOTSTRAP_EXCEPTION**. Runtime environment detection is read-only and used for platform identification, not for arbitrary configuration.

### 5. `installer/plan.py`

- `os.environ.get("HIVE_BUNDLED_GIT")` — **BOOTSTRAP_EXCEPTION**. Build-time environment override.
- `os.environ.get("HOME")` — **BOOTSTRAP_EXCEPTION**. Used for default install target before configuration exists.
- Uses `lib/hive_path` resolvers — **PARTIALLY_MIGRATED**. Installer still reads bootstrap roots directly.

Decision: installer is **BOOTSTRAP_ONLY** for configuration. It must use `config_engine` for all subsystem settings once the engine is available.

### 6. `installer/preflight.py`

- `os.environ.get("HOME")`, `os.environ.get("PREFIX")`, `os.environ.get("TMPDIR")`, `os.environ.get("HIVE_HOME")` — **BOOTSTRAP_EXCEPTION**. Environment detection only.
- Uses `lib/hive_path` — **BOOTSTRAP_ONLY**.

### 7. `installer/legacy.py`

- `os.environ.get("HOME")` — **BOOTSTRAP_EXCEPTION**. Legacy installation detection.

### 8. `security/vault/backend.py`

- `os.environ.get("HOME")` — **BOOTSTRAP_EXCEPTION / PARTIALLY_MIGRATED**. Vault currently falls back to `~/.hive/vault` when no explicit vault_dir is given.

Decision: vault is **PARTIALLY_MIGRATED**. Vault directory should be obtained from `config_engine.get_config("vault")["path"]`; the HOME fallback is documented as bootstrap debt.

### 9. `security/vault/migration.py`

- `os.environ.get("HOME")` — **LEGACY_COMPATIBILITY**. Scans `~/.hive_auth` for legacy credentials during migration planning.

### 10. `hive_broker/version.py`

- `os.environ.get("HIVE_SOURCE_COMMIT")` — **BOOTSTRAP_EXCEPTION**. Build-time source commit metadata, not user configuration.

### 11. `updates/updater.py`

- `json.loads(self.journal_path.read_text(...))` — **PARTIALLY_MIGRATED**. Reads update journal state, not user configuration. Journals are internal state files, not configuration.

### 12. `bin/hive`

- `load_metadata(repo_root)` reads `hive-canonical.json` — **BOOTSTRAP_EXCEPTION**. Repository canonical metadata, not subsystem configuration.
- `hive config` delegation to `config_engine.cli` — **MIGRATED**.

## Subsystem classification

| Subsystem | Status | Notes |
| --------- | ------ | ----- |
| `hive_broker` | **FULLY_MIGRATED** | Reads state/log roots via `config_engine.get_config("runtime")` |
| `operations_center` | **FULLY_MIGRATED** | Reads state/log roots via `config_engine.get_config("runtime")` |
| `services` | **FULLY_MIGRATED** | Reads manifest dirs and roots via `config_engine.get_config("services")` |
| `installer` | **BOOTSTRAP_ONLY** | Uses bootstrap path layer; no subsystem configuration parsed directly |
| `updates` | **PARTIALLY_MIGRATED** | Journal state is internal, not configuration; update settings should come from `config_engine` when invoked through broker |
| `recovery` | **DEFERRED** | No direct config parsing found in current code; recovery settings should be added to `config_engine` schema and consumed by recovery CLI |
| `vault` | **PARTIALLY_MIGRATED** | Vault path should come from `config_engine.get_config("vault")`; HOME fallback is bootstrap debt |
| `runtime/path layer` | **BOOTSTRAP_EXCEPTION** | `lib/hive_path.py` is the explicit bootstrap layer |

## Direct production config readers remaining

All remaining direct reads fall into one of:

1. **Bootstrap exceptions** (`HIVE_REPO_ROOT`, `HOME`, `HIVE_PROFILE`, `HIVE_SOURCE_COMMIT`, `HIVE_BUNDLED_GIT`, `hive-canonical.json`).
2. **Internal state files** (update journal).
3. **Legacy compatibility code** (vault migration scanning).

No production subsystem parses arbitrary Hive configuration files directly.

## Accepted exceptions

- `lib/hive_path.py` — bootstrap root resolution only.
- `lib/hive_runtime.py` — environment detection only.
- `installer/*` — bootstrap path detection only.
- `security/vault/backend.py` — bootstrap vault_dir fallback.
- `security/vault/migration.py` — legacy credential migration scan.
- `hive_broker/version.py` — build-time commit override.
- `updates/updater.py` — internal journal state.

## Deferred configuration debt

- `updates/` should consume `config_engine.get_config("updates")` when invoked through the broker.
- `security/vault/cli.py` should obtain vault path from `config_engine.get_config("vault")` and remove HOME fallback.
- `recovery/` should add a recovery CLI consumer that reads `config_engine.get_config("recovery")`.

These are bounded, documented, and do not contradict single configuration authority.
