# Configuration Migration Plan

## Old config sources

- `~/.config/hive/env.sh`
- `~/.hive_auth/passwd` (base64)
- `~/.bashrc` Hive integration lines
- `~/.termux/boot/00-hive-secure.sh`

## Migration to new schema

| Old item | New item | Migration action |
|----------|----------|------------------|
| `env.sh` | `~/.config/hive/config.yaml` | Import on first run, preserve original |
| base64 passwd | vault | Re-encrypt on first unlock; keep backup until verified |
| bashrc source line | new shell-integration.sh path | Update line, preserve old as comment |
| boot script | `core/session-gate/hive-session-gate.sh` | Replace with compatibility wrapper |

## Safety

- Always backup old config before migration.
- Run migration in dry-run mode by default.
- Allow operator to skip migration and use legacy mode.
