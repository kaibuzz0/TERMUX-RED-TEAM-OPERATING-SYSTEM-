# Hive OS Offline Update Bundles

Offline bundles are the primary update delivery mechanism.

## Bundle format

A gzipped tar archive containing:

- `metadata.json`
- `manifest.json`
- runtime artifacts at relative paths

## Verification steps

1. Extract to a temporary directory.
2. Validate paths (no `..`, absolute paths, symlinks, device files).
3. Check expanded size and file-count limits.
4. Parse and validate `metadata.json` schema.
5. Verify Ed25519 signature against trust store.
6. Check platform, architecture, security sequence, and revocation.
7. Verify artifact sizes and digests.
8. Verify manifest digests against files.

## Safety limits

- Max expanded size: 512 MiB
- Max file count: 50,000
