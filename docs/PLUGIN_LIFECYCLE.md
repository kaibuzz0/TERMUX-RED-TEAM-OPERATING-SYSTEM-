# Plugin Lifecycle

Plugins move through explicit lifecycle states. Default state is `DISABLED`.

## States

- `DISCOVERED`
- `VALIDATED`
- `INCOMPATIBLE`
- `DISABLED` (default)
- `ENABLED`
- `DEGRADED`
- `ERROR`
- `QUARANTINED`
- `REMOVED`

## Rules

- Plugins are discovered from staged bundles.
- Validation does not execute plugin code.
- Install planning does not execute plugin code.
- Plugins are never auto-enabled.
- `auto_start` is always treated as `false` in Milestone 16.
- Repeated failures may transition a plugin to `DEGRADED` or `QUARANTINED`.

## CLI

```
hive plugin list
hive plugin inspect ID
hive plugin validate PATH
hive plugin install PATH --plan
hive plugin capabilities ID
hive plugin status ID
hive plugin audit ID
hive plugin config ID
hive plugin enable ID
hive plugin disable ID
hive plugin remove ID --plan
```
