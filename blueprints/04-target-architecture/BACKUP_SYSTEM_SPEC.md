# Backup System Specification

## Backup types

| Type | Scope | Frequency | Storage |
|------|-------|-----------|---------|
| Config backup | `~/.config/hive/` | On every update/repair | `~/.local/share/hive/backups/config/` |
| State backup | `~/.local/share/hive/state/` | On every update/repair | `~/.local/share/hive/backups/state/` |
| Vault metadata backup | Vault file index, not keys | On every update/repair | `~/.local/share/hive/backups/vault/` |
| Runtime backup | Active runtime prefix | After successful update | `~/.local/share/hive/runtimes/` |
| Full data backup | Config + state + workspace artifacts | Operator-triggered | Configurable |

## Requirements

- Backups are created before any destructive or mutating operation.
- Backups include a manifest with hashes.
- Config backups exclude secrets.
- Vault backups include only encrypted vault files, not plaintext keys.
- Backups are versioned by timestamp.
- Retention policy is configurable (default: keep last 10 config, 5 full).
- Backup verification command (`hive backup verify`) checks manifest hashes.
- Restore preview (`hive backup restore --preview`) shows what would change.
- Restore requires confirmation.
- Backups are stored within the Termux app data; export to shared storage requires explicit operator action.

## Integrity

- Manifest file: JSON with file paths, SHA-256 hashes, and backup timestamp.
- Verification re-computes hashes and reports mismatches.

## Encryption

- Backups of vault files are already encrypted.
- Optional full-backup encryption with operator passphrase.

## Failure behavior
- If backup fails before a mutating operation, the operation is cancelled.
