# Minimum RC API/Schema Inventory

**Commit:** `e27e0c4` | **Tag:** `1.0.0-rc.1`

---

## Enforcement Points (13)

| # | Module | File:Line | Accepts | Rejects With |
|---|--------|-----------|---------|-------------|
| 1 | `hive_broker` | `schema.py:24` | `== 1` | `ManifestError` |
| 2 | `plugin_sdk` | `manifest.py:117` | `== 1` | `PluginManifestError` |
| 3 | `policy_engine` | `requests.py:103` | `in {1}` | `PolicyRequestError` |
| 4 | `services` | `schema.py:37` | `== 1` | `ServiceConfigError` |
| 5 | `installer` | `activate.py:151` | `== 1` | `ActivationSafetyError` |
| 6 | `installer` | `activate.py:187` | `== 1` | `ActivationSafetyError` |
| 7 | `release_engine` | `registry.py:15` | `== 1` (write) | None (read unvalidated) |
| 8 | `security/vault` | `format.py:83` | `in {1}` | `VaultFormatError` |
| 9 | `updates` | `metadata.py:93` | `== 1` | `BundleError` |
| 10 | `lib` | `hive_path.py:105` | `== 1` | `CanonicalMetadataError` |
| 11 | `operations_center` | `schema.py:41` | `== 1` | `OperationsCenterError` |
| 12 | `config_engine` | `defaults.py` | `min_value=1` | FieldSpec validation |
| 13 | `lib` | `hive_service_loader.py:215` | `in (1, 2)` | `ServiceSchemaError` |

## Constants

```python
plugin_sdk.schema.SCHEMA_VERSION = 1
policy_engine.requests.KNOWN_SCHEMA_VERSIONS = {1}
services.schema.SCHEMA_VERSION = 1
release_engine.registry.REGISTRY_SCHEMA_VERSION = 1
updates.metadata.METADATA_SCHEMA_VERSION = 1
security.vault.format.SUPPORTED_SCHEMA_VERSIONS = {1}
installer.activate.ACTIVE_POINTER_SCHEMA_VERSION = 1
installer.activate.RELEASE_SCHEMA_VERSION = 1
```

## Config Engine Schemas (10 at version 1)

runtime, network, services, security, updates, plugins, logging, telemetry, recovery, installer

## Exceptions (3)

1. `lib/hive_service_loader.py` — intentionally supports v1 and v2
2. `release_engine/registry.py` — `_load()` does not validate schema version on read
3. `config_engine/migration.py` — exists but not called by any production path

## Verification

- **Tests:** `tests/test_m19_api_schema_freeze.py` — 19 tests, all pass
- **Full suite:** 1270 passed, 0 failed at `e27e0c4`