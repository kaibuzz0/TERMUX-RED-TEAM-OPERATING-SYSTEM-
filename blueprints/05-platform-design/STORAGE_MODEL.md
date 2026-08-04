# Storage Model

## Layout

```text
~/.config/hive/          # configuration
~/.local/share/hive/     # runtime state, logs, backups, workspaces, vault
~/storage/               # Android shared storage (only if permission granted)
```

## Policy

- App-private storage is preferred for sensitive data.
- Shared storage is used only for explicit exports/imports.
- Vault files never reside in shared storage unencrypted.
- Cache directories are bounded.
- Backups are versioned and rotated.

## Quotas

- Configurable per-workspace storage limit.
- Log size cap.
- Backup retention count.
