# Hive OS Credential Migration

**Milestone 8**

## Legacy credential

The active legacy credential store is `$HOME/.hive_auth/passwd`, created by `Hive Ops Final/bin/hive-secure-login`. It stores the operator password and PIN as base64-encoded plaintext.

## Migration process

1. `hive vault migrate-legacy --plan` detects the legacy file and returns a non-mutating plan.
2. The operator initializes an encrypted vault.
3. `hive vault migrate-legacy --apply` (future) decodes the legacy value only in memory, encrypts it into the vault, and preserves the original file in a quarantine directory.
4. After physical Termux validation, `hive-secure-login` can be updated to use the vault.

## Restrictions

- No automatic deletion of original credentials.
- No logging of decoded values.
- No migration without operator authentication.
- No migration of unknown formats.
