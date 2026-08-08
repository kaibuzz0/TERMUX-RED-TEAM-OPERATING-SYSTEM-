# Milestone 19 — RC API/Schema Inventory

**Commit:** `1044454`  
**Tag:** `1.0.0-rc.1` → `1044454`  
**Date:** 2026-08-08  
**Total Tests:** 1270 passed, 0 failed, 0 skipped  
**Files:** 69

---

## 1. Executive Summary

Hive OS 1.0.0-rc.1 operates a **strict schema freeze** at `schema_version = 1` across all production modules. No version negotiation exists for schema versions. Any document, manifest, request, or metadata object with a schema version other than `1` is **rejected at the validation boundary** with a descriptive error.

The only exceptions are:
- `lib/hive_service_loader.py` intentionally supports schema versions **1 and 2** (backward-compatible service loader shim).
- `release_engine.registry._load()` does not validate schema version on read (returns whatever is on disk; validation is implicit via `REGISTRY_SCHEMA_VERSION` on write).
- `config_engine.migration` infrastructure exists but is **not called by any production loader**.

---

## 2. Schema Enforcement Matrix

| Module | File | Enforcement Point | Accepts | Rejects With | Constant |
|--------|------|-------------------|---------|--------------|----------|
| **Broker manifest** | `hive_broker/schema.py:24` | `validate_manifest()` | `== 1` | `ManifestError("Unsupported manifest schema version")` | hardcoded |
| **Plugin manifest** | `plugin_sdk/manifest.py:117` | `load_manifest()` | `== SCHEMA_VERSION (1)` | `PluginManifestError("unsupported schema_version")` | `SCHEMA_VERSION = 1` |
| **Policy request** | `policy_engine/requests.py:103` | `PolicyRequest.from_dict()` | `in KNOWN_SCHEMA_VERSIONS {1}` | `PolicyRequestError("Unsupported policy request schema version")` | `KNOWN_SCHEMA_VERSIONS = {1}` |
| **Service manifest** | `services/schema.py:37` | `validate_manifest()` | `== SCHEMA_VERSION (1)` | `ServiceConfigError("Unsupported schema version")` | `SCHEMA_VERSION = 1` |
| **Active pointer** | `installer/activate.py:151` | `_active_pointer()` | `== ACTIVE_POINTER_SCHEMA_VERSION (1)` | `ActivationSafetyError("Unknown active pointer schema")` | `ACTIVE_POINTER_SCHEMA_VERSION = 1` |
| **Release metadata** | `installer/activate.py:187` | `_read_release_metadata()` | `== RELEASE_SCHEMA_VERSION (1)` | `ActivationSafetyError` | `RELEASE_SCHEMA_VERSION = 1` |
| **Release registry** | `release_engine/registry.py:15` | `_save()` (write) | `== REGISTRY_SCHEMA_VERSION (1)` | N/A (implicit on init) | `REGISTRY_SCHEMA_VERSION = 1` |
| **Vault format** | `security/vault/format.py:83` | `deserialize()` | `in SUPPORTED_SCHEMA_VERSIONS {1}` | `VaultFormatError("Unsupported vault schema version")` | `SUPPORTED_SCHEMA_VERSIONS = {1}` |
| **Update metadata** | `updates/metadata.py:93` | `load_metadata()` | `== METADATA_SCHEMA_VERSION (1)` | `BundleError("Unsupported metadata schema version")` | `METADATA_SCHEMA_VERSION = 1` |
| **Canonical metadata** | `lib/hive_path.py:105` | `load_canonical_metadata()` | `== 1` | `CanonicalMetadataError("unsupported schema_version")` | hardcoded |
| **Operations Center** | `operations_center/schema.py:41` | `validate_manifest()` | `== 1` | `OperationsCenterError` | hardcoded |
| **Config schemas** | `config_engine/defaults.py` | `ConfigSchema.validate()` | `== version (1)` | N/A (FieldSpec default=1) | `version=1` per schema |
| **Service loader** | `lib/hive_service_loader.py:215` | `load_service_manifest()` | `in (1, 2)` | `ServiceSchemaError` | hardcoded tuple |

---

## 3. Output Metadata Schema Versions

All structured output includes `schema_version: 1` for forward compatibility detection:

| Module | File | Output Key |
|--------|------|------------|
| Broker | `hive_broker/__init__.py` | `"schema_version": 1` |
| Broker capabilities | `hive_broker/capabilities.py` | `"schema_version": 1` |
| Broker dispatcher | `hive_broker/dispatcher.py` | `"schema_version": 1` |
| Broker policy | `hive_broker/policy.py` | `"schema_version": 1` |
| Policy audit | `policy_engine/audit.py` | `"schema_version": 1` |
| Policy decisions | `policy_engine/decisions.py` | `schema_version: int = 1` |
| Policy engine | `policy_engine/engine.py` | `"schema_version": 1` |
| Policy evaluator | `policy_engine/evaluator.py` | `schema_version=1` |
| Installer schema | `installer/schema.py` | `schema_version: int = 1` |
| Installer plan | `installer/plan.py` | `schema_version=1` |
| Release builder | `release_engine/builder.py` | `"schema_version": 1` |
| Release SBOM | `release_engine/sbom.py` | `"schema_version": 1` |
| Operations Center CLI | `operations_center/cli.py` | `"schema_version": 1` |
| Operations Center collectors | `operations_center/collectors.py` | `"schema_version": 1` |
| Operations Center data sources | `operations_center/data_sources.py` | `"schema_version": 1` |
| Config engine defaults | `config_engine/defaults.py` | `"schema_version": 1` per profile |

---

## 4. Config Engine Schema Registry

`config_engine/defaults.py` registers **10 schemas**, all at `version=1`:

1. `runtime` — profile, log_level, log_root, state_root, config_root, data_root, cache_root, temp_root, repo_root, max_log_size_mb, max_log_count
2. `network` — interface, dhcp, static_ip, gateway, dns
3. `services` — enabled, disabled, manifests_dir
4. `security` — vault_enabled, vault_key_id, vault_path
5. `updates` — channel, auto_check, auto_download, auto_install, max_sequence_delta
6. `plugins` — enabled, disabled, registry_path, max_plugin_memory_mb
7. `logging` — level, format, destinations, max_size_mb, max_count
8. `telemetry` — enabled, endpoint, interval, batch_size
9. `recovery` — enabled, backup_interval, retention_days, max_backups
10. `installer` — staging_dir, verify_signatures, allow_downgrades

All define `schema_version: FieldSpec(int, required=True, min_value=1, default=1)`.

---

## 5. Migration System

**File:** `config_engine/migration.py`

- `Migration` dataclass: `name`, `from_version`, `to_version`, `transform`
- `MigrationRegistry`: ordered list of migrations per subsystem
- `migrate()`: applies migrations sequentially, validates `schema_version` bump
- **Status:** Infrastructure exists but **not invoked by any production code path**
- `load_json_file()` in `config_engine/loader.py` contains no migration logic
- Documented as accepted debt for post-1.0 evolution

---

## 6. Compatibility Negotiation (Distinct from Schema Freeze)

**File:** `plugin_sdk/compatibility.py`

- `negotiate_compatibility(manifest, broker_caps)` performs **runtime version matching** between plugin `minimum_hive_version` / `minimum_sdk_version` and the actual Hive runtime version.
- This is **not** schema version negotiation — it validates semantic version compatibility after schema validation has already passed.
- The word "negotiation" appears in this module and `hive_broker/capabilities.py` (docstring only) but **never in conjunction with `schema_version`**.

---

## 7. Exceptions / Accepted Debt

| Item | Module | Description |
|------|--------|-------------|
| Service loader backward compat | `lib/hive_service_loader.py` | Intentionally supports schema versions 1 and 2 for service manifest loading |
| Registry read unvalidated | `release_engine/registry.py` | `_load()` does not validate `schema_version`; writes use `REGISTRY_SCHEMA_VERSION = 1` |
| Migration unused | `config_engine/migration.py` | Migration system present but not called by any production path |

---

## 8. Verification

**Test file:** `tests/test_m19_api_schema_freeze.py` (19 tests)

| Test | Assertion |
|------|-------------|
| `test_manifest_schema_version_1_accepted` | Broker manifest v1 passes |
| `test_manifest_schema_version_2_rejected` | Broker manifest v2 raises `ManifestError` |
| `test_plugin_manifest_schema_version_1_accepted` | Plugin manifest v1 passes |
| `test_plugin_manifest_schema_version_2_rejected` | Plugin manifest v2 raises `PluginManifestError` |
| `test_policy_request_schema_version_1_accepted` | Policy request v1 passes |
| `test_policy_request_schema_version_2_rejected` | Policy request v2 raises `PolicyRequestError` |
| `test_service_manifest_schema_version_1_accepted` | Service manifest v1 passes |
| `test_service_manifest_schema_version_2_rejected` | Service manifest v2 raises `ServiceConfigError` |
| `test_active_pointer_schema_version_mismatch_rejected` | Active pointer v2 raises `ActivationSafetyError` |
| `test_release_metadata_schema_version_mismatch_rejected` | Release metadata v2 raises `ActivationSafetyError` |
| `test_release_registry_schema_version_1_accepted` | Registry default v1 verified |
| `test_release_registry_load_does_not_validate_schema_version` | Registry `_load` unvalidated documented |
| `test_migration_system_exists` | Migration class present |
| `test_migration_not_called_by_loader` | `load_json_file` has no migration logic |
| `test_plugin_sdk_has_compatibility_negotiation` | `negotiate_compatibility` exists but is version-matching, not schema negotiation |
| `test_no_schema_version_negotiation_in_production` | grep confirms no `schema_version.*negotiat` in production |
| `test_all_schema_version_defaults_are_1` | All constants verified == 1 |
| `test_config_engine_schema_default_is_1` | `ConfigSchema.version == 1` |
| `test_policy_engine_schema_default_is_1` | `TypedSchema.version == 1` |

---

## 9. Glossary

| Term | Definition |
|------|------------|
| `schema_version` | Integer field in every persisted JSON document indicating the shape/semantics of the document |
| `SCHEMA_VERSION` | Module-level constant defining the canonical version accepted by that module |
| `KNOWN_SCHEMA_VERSIONS` | Set of acceptable versions (currently `{1}` everywhere except service loader) |
| `ConfigSchema` | Typed validator with `version` attribute, used by config engine |
| `TypedSchema` | Generic validator used by policy engine |
| Migration | Forward-only schema evolution mechanism (not exercised in 1.0.0-rc.1) |

---

*This inventory is authoritative for the 1.0.0-rc.1 release candidate. Any schema version change after this point requires a formal RFC, a migration plan, and updates to this document.*