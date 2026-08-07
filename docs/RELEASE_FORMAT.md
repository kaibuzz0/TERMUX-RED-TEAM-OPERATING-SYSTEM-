# Release Format

A release bundle contains:

- `metadata.json` — release metadata and signature
- `manifest.json` — canonical file manifest with SHA-256 digests
- `payload/` — included files (layout may be flat)

The bundle is a deterministic gzip-compressed tar archive.

## Exclusions

- `.git/`, `.github/`
- `tests/`, `blueprints/`
- `__pycache__/`, `.pytest_cache/`
- user config, logs, vault files, secrets
- private keys
- developer machine paths
