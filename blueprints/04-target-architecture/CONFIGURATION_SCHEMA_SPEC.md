# Configuration Schema Specification

## Files

| File | Purpose |
|------|---------|
| `core/etc/defaults.yaml` | Built-in defaults |
| `~/.config/hive/config.yaml` | User overrides |
| `~/.config/hive/profiles/` | Profile-specific overrides |

## Top-level schema

```yaml
schema_version: 2

platform:
  profile: termux-standard  # or termux-api, root-enhanced, desktop-linux, custom-rom-research

paths:
  runtime_dir: "~/.local/share/hive"
  config_dir: "~/.config/hive"
  log_dir: "~/.local/share/hive/logs"
  backup_dir: "~/.local/share/hive/backups"
  workspace_dir: "~/.local/share/hive/workspaces"

session_gate:
  enabled: true
  auto_lock_minutes: 10
  max_attempts: 3
  lockout_seconds: 60

vault:
  kdf: argon2id
  kdf_params:
    memory_kb: 65536
    iterations: 3
    parallelism: 1
  auto_lock_minutes: 5

services:
  default_bind: 127.0.0.1
  allow_remote_bind: false
  log_retention_days: 30

agent:
  max_delegations: 0
  default_max_runtime_minutes: 30
  default_max_changed_files: 10
  require_approval_for_destructive: true

audit:
  enabled: true
  retention_days: 30
  redact_secrets: true

update:
  channel: signed-release
  verify_signatures: true
  rollback_retention_count: 3

network:
  default_mode: deny-by-default
  dns_mode: termux-default
```

## Validation

- Unknown keys rejected.
- Deprecated keys warned.
- Path values expanded and validated to be within expected directories.
- Network modes restricted to allowed enum values.
- Profile value restricted to known profiles.

## Profile overrides

Each profile under `~/.config/hive/profiles/` overrides the base config. The active profile is selected by `platform.profile`.
