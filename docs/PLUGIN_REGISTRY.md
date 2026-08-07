# Plugin Registry

Persistent registry stores plugin state under the state root.

Fields:

- plugin_id, version, installation_id
- manifest_digest, bundle_digest
- signature_trust, requested/granted capabilities
- configuration_digest, state, install timestamp
- publisher, SDK compatibility, quarantine_state

Atomic writes, schema version, corruption handling.

Plugins cannot modify their own registry record directly.
