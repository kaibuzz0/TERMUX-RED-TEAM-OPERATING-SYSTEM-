# Plugin Configuration

Plugin configuration is owned by the Configuration Engine and namespaced under `plugins.<plugin_id>`.

## Rules

- No direct config-file parsing by plugins.
- No arbitrary environment override.
- No global config writes.
- No plaintext secret storage.
- Vault references for secret material.
- Config previews redact secrets.
- Plugins cannot edit another plugin namespace.
- Plugins cannot edit core Hive config.

## Schema

Plugins declare typed configuration schemas. Unknown keys are rejected when strict mode is enabled.
