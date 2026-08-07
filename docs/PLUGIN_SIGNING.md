# Plugin Signing

Milestone 16 supports signature metadata without requiring production signing infrastructure.

## Trust States

- `UNSIGNED`
- `SIGNED_UNTRUSTED`
- `SIGNED_TRUSTED`
- `INVALID_SIGNATURE`
- `REVOKED`

## Policy

Production profiles may deny unsigned plugins. Development profiles may inspect unsigned plugins but must not silently trust them.

## Private Keys

No publisher private keys are stored in this repository.
