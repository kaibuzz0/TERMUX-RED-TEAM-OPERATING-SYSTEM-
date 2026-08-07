# Plugin Development

This guide explains how to build a safe, read-only Hive OS plugin.

## Example

See `examples/plugins/hive-status/`.

## Steps

1. Create a `manifest.json` with schema version 1.
2. Request only read-only capabilities.
3. Set `network: deny` and `secrets: []`.
4. Keep `auto_start: false`.
5. Use `PluginClient` for Broker requests.
6. Do not import broker dispatcher internals.
7. Do not call shell or subprocess.
8. Test with `hive plugin validate PATH`.
