# Hive OS Release Signing

## Algorithm

Ed25519 via the `cryptography` library.

## Key management

- Release signing private key is held offline.
- Runtime trust store contains PEM-encoded public keys with key IDs.
- Key rotation is supported by adding new public keys and revoking old ones.
- Revocation is tracked by `revocation.sequence`.

## Signing canonicalization

Metadata is serialized deterministically with sorted keys and compact separators before signing.

## Security boundary

Private keys are never read by the runtime. The runtime only verifies signatures.
