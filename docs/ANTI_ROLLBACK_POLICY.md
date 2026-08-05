# Hive OS Anti-Rollback Policy

## Security sequence

Each release carries a monotonically increasing integer `security_sequence`.

## Rejected updates

- Lower security sequence than current.
- Known revoked security sequence.
- Incompatible platform or architecture.
- Unknown metadata schema.

## Emergency downgrade

Allowed only through `EMERGENCY_RECOVERY_BUNDLE` path with:

- typed operator confirmation
- verified signed bundle
- recorded reason
- recovery journal
- preserved current runtime
- explicit security warning
