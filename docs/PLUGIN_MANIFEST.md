# Plugin Manifest

Every plugin must ship a `manifest.json` with the strict schema described here.

## Schema

```json
{
  "schema_version": 1,
  "plugin": {
    "id": "example.status-plugin",
    "name": "Example Plugin",
    "version": "1.0.0",
    "sdk_version": "1.0",
    "entrypoint": "example_plugin.main",
    "type": "client"
  },
  "compatibility": {
    "minimum_hive_version": "1.0.0-dev",
    "required_broker_version": "1.0",
    "required_capabilities": ["service.status"]
  },
  "permissions": {
    "requested_capabilities": ["service.status"],
    "filesystem": [],
    "network": "deny",
    "secrets": []
  },
  "lifecycle": {
    "auto_start": false
  }
}
```

## Rules

- Unknown schema versions fail closed.
- Unknown fields fail closed.
- Duplicate keys are rejected.
- Plugin IDs must match `[a-z][a-z0-9._-]*[a-z0-9]`.
- Versions must be semantic versions.
- Wildcard, shell, policy, vault, update, recovery, and service mutation capabilities are forbidden.
- `auto_start` defaults to `false`.
- `network` defaults to `deny`.
- `secrets` must be empty in Milestone 16.
