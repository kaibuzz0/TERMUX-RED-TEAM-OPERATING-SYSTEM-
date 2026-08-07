# Manifest Schema

See `docs/PLUGIN_MANIFEST.md` for user-facing docs and `plugin_sdk/manifest.py` for implementation.

## Enforcement

- JSON parse rejects duplicate keys.
- Unknown top-level and section fields rejected.
- Semantic version validation.
- Capability format and deny-list validation.
- Filesystem path constraints.
- Network default deny.
- Empty secrets list.
