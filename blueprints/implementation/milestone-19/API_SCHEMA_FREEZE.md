# Milestone 19 — API / Schema Freeze Blueprint

**Status:** Implemented  
**Commit:** `87482d7` (tag `1.0.0-rc.1`)  
**Author:** Milestone 19 Hardening  
**Date:** 2026-08-08

---

## 1. Context

Hive OS 1.0.0-rc.1 enters **feature freeze** with a strict API and schema version freeze. All persisted JSON documents, manifests, requests, and metadata objects across the system use `schema_version = 1`. No backward-compatibility shims, no version negotiation, and no migration paths are exercised on production code paths.

This blueprint documents the freeze boundaries, enforcement mechanisms, exceptions, and verification.

---

## 2. Goals

1. **Guarantee** that every production module hardcodes `schema_version == 1` and rejects any other value at the validation boundary.
2. **Prove** that no schema version negotiation logic exists in production code.
3. **Document** the three accepted exceptions explicitly.
4. **Provide** a single authoritative reference for post-1.0 schema evolution planning.

### Non-Goals

- Do not add migration logic to production loaders.
- Do not introduce schema version 2 support anywhere except the already-supported service loader shim.
- Do not design a generic schema registry or dynamic validation system.

---

## 3. Implementation

### 3.1 Enforcement Points (13 modules)

| # | Module | File | Function / Method | Rejects With |
|---|--------|------|-------------------|-------------|
| 1 | `hive_broker` | `schema.py:24` | `validate_manifest()` | `ManifestError("Unsupported manifest schema version")` |
| 2 | `plugin_sdk` | `manifest.py:117` | `load_manifest()` | `PluginManifestError("unsupported schema_version")` |
| 3 | `policy_engine` | `requests.py:103` | `PolicyRequest.from_dict()` | `PolicyRequestError("Unsupported policy request schema version")` |
| 4 | `services` | `schema.py:37` | `validate_manifest()` | `ServiceConfigError("Unsupported schema version")` |
| 5 | `installer` | `activate.py:151` | `_active_pointer()` | `ActivationSafetyError("Unknown active pointer schema")` |
| 6 | `installer` | `activate.py:187` | `_read_release_metadata()` | `ActivationSafetyError` |
| 7 | `release_engine` | `registry.py:15` | `_save()` (implicit on init) | None — read unvalidated |
| 8 | `security/vault` | `format.py:83` | `deserialize()` | `VaultFormatError("Unsupported vault schema version")` |
| 9 | `updates` | `metadata.py:93` | `load_metadata()` | `BundleError("Unsupported metadata schema version")` |
| 10 | `lib` | `hive_path.py:105` | `load_canonical_metadata()` | `CanonicalMetadataError("unsupported schema_version")` |
| 11 | `operations_center` | `schema.py:41` | `validate_manifest()` | `OperationsCenterError` |
| 12 | `config_engine` | `defaults.py` | `ConfigSchema.validate()` | FieldSpec `min_value=1` |
| 13 | `lib` | `hive_service_loader.py:215` | `load_service_manifest()` | `ServiceSchemaError` — accepts `(1, 2)` |

### 3.2 Constants

```python
# plugin_sdk/schema.py
SCHEMA_VERSION: int = 1

# policy_engine/requests.py
KNOWN_SCHEMA_VERSIONS: set[int] = {1}

# services/schema.py
SCHEMA_VERSION: int = 1

# release_engine/registry.py
REGISTRY_SCHEMA_VERSION: int = 1

# updates/metadata.py
METADATA_SCHEMA_VERSION: int = 1

# security/vault/format.py
SUPPORTED_SCHEMA_VERSIONS: set[int] = {1}

# installer/activate.py
ACTIVE_POINTER_SCHEMA_VERSION = 1
RELEASE_SCHEMA_VERSION = 1
```

### 3.3 Config Engine Schema Registry (10 schemas at version 1)

All schemas in `config_engine/defaults.py` define:

```python
"schema_version": FieldSpec("schema_version", int, required=True, min_value=1, default=1)
```

Registered schemas:
1. `runtime` — profiles: minimal, development, portable, production, termux, desktop-linux, windows
2. `network` — interface, dhcp, static_ip, gateway, dns
3. `services` — enabled, disabled, manifests_dir
4. `security` — vault_enabled, vault_key_id, vault_path
5. `updates` — channel, auto_check, auto_download, auto_install, max_sequence_delta
6. `plugins` — enabled, disabled, registry_path, max_plugin_memory_mb
7. `logging` — level, format, destinations, max_size_mb, max_count
8. `telemetry` — enabled, endpoint, interval, batch_size
9. `recovery` — enabled, backup_interval, retention_days, max_backups
10. `installer` — staging_dir, verify_signatures, allow_downgrades

### 3.4 Output Metadata

All structured output embeds `"schema_version": 1` for forward-compatibility detection:

- `hive_broker/__init__.py`, `capabilities.py`, `dispatcher.py`, `policy.py`
- `policy_engine/audit.py`, `decisions.py`, `engine.py`, `evaluator.py`
- `installer/schema.py`, `plan.py`
- `release_engine/builder.py`, `sbom.py`
- `operations_center/cli.py`, `collectors.py`, `data_sources.py`, `schema.py`
- `config_engine/defaults.py` (per-profile runtime blocks)

### 3.5 Migration System (Non-Production)

**File:** `config_engine/migration.py`

- `Migration` dataclass: `name`, `from_version`, `to_version`, `transform`
- `MigrationRegistry`: ordered list per subsystem
- `migrate()`: sequential application with `schema_version` bump validation
- **Status:** Infrastructure present; **not called by any production loader**
- `load_json_file()` contains zero migration logic
- Post-1.0 evolution path only

### 3.6 Compatibility Negotiation (Distinct)

**File:** `plugin_sdk/compatibility.py`

- `negotiate_compatibility(manifest, broker_caps)` performs **runtime semantic version matching** between plugin `minimum_hive_version` / `minimum_sdk_version` and the runtime.
- This is **not** schema version negotiation — it runs after schema validation has already passed.
- No production module contains `schema_version.*negotiat` logic.

---

## 4. Verification

**Test file:** `tests/test_m19_api_schema_freeze.py` (19 tests, all pass)

| Test Class | Tests | Coverage |
|-----------|-------|----------|
| `TestBrokerManifestSchemaFreeze` | 2 | Accept v1, reject v2 |
| `TestPluginManifestSchemaFreeze` | 2 | Accept v1, reject v2 |
| `TestPolicyRequestSchemaFreeze` | 2 | Accept v1, reject v2 |
| `TestServiceManifestSchemaFreeze` | 2 | Accept v1, reject v2 |
| `TestInstallerActivateSchemaFreeze` | 2 | Active pointer + release metadata reject v2 |
| `TestReleaseRegistrySchemaFreeze` | 2 | Default v1 verified; `_load` unvalidated documented |
| `TestConfigMigrationNotOnProductionPaths` | 2 | Migration exists; loader does not call it |
| `TestCompatibilityNegotiationDistinct` | 2 | `negotiate_compatibility` exists; no schema negotiation in production |
| `TestSchemaFreezeDefaults` | 3 | All constants == 1; `ConfigSchema.version == 1`; `TypedSchema.version == 1` |

**Full suite:** 1270 passed, 0 failed, 0 skipped at `87482d7`.

---

## 5. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Post-1.0 schema evolution requires migration infrastructure | Medium | Medium | Migration system already exists in `config_engine/migration.py` |
| R2 | Registry `_load()` does not validate schema version on read | Low | Low | Writes enforce `REGISTRY_SCHEMA_VERSION = 1`; corrupted file would fail downstream parsing |
| R3 | Service loader supports v1 and v2, creating a divergence point | Low | Low | Intentional backward-compat shim; v2 is a legacy format, not an active evolution path |
| R4 | Hardcoded `== 1` checks require coordinated updates across 13 modules | Medium | High | This blueprint serves as the canonical reference for all touch points |

---

## 6. Decisions and Consequences

| Decision | Consequence |
|----------|-------------|
| Reject all schema versions != 1 at validation boundaries | Simple, fail-closed behavior; no ambiguity about supported formats |
| Do not invoke migration system on production paths | No runtime overhead; evolution must be explicitly designed post-1.0 |
| Allow service loader to accept v1 and v2 | Preserves compatibility with existing service manifests; only exception to strict freeze |
| Registry read unvalidated | Read-after-write consistency assumed; corruption would raise JSON parse error before schema mismatch matters |
| Embed `schema_version: 1` in all output | Future consumers can detect format version without heuristics |

---

## 7. References

- `RC_API_SCHEMA_INVENTORY.md` — comprehensive reference catalog of all 110 schema_version references
- `tests/test_m19_api_schema_freeze.py` — 19-test verification suite
- `config_engine/migration.py` — migration infrastructure (non-production)
- `plugin_sdk/compatibility.py` — runtime version negotiation (distinct from schema freeze)

---

*This blueprint is authoritative for Hive OS 1.0.0-rc.1. Any schema version change after release requires an RFC, updates to this document, and regression tests covering all 13 enforcement points.*