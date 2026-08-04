# Command API Specification

## Interface

The canonical command API is the `hive` CLI with `--json` output. The TUI, Hermes plugin, and scripts all consume this API.

## Request format

```bash
hive [global-options] COMMAND [subcommand] [args]
```

## Response envelope (JSON mode)

```json
{
  "command": "hive status",
  "success": true,
  "exit_code": 0,
  "timestamp": "2026-08-03T12:00:00Z",
  "platform_profile": "termux-standard",
  "warnings": [],
  "errors": [],
  "data": {}
}
```

## Error envelope

```json
{
  "command": "hive update apply",
  "success": false,
  "exit_code": 8,
  "timestamp": "2026-08-03T12:00:00Z",
  "platform_profile": "termux-standard",
  "warnings": ["Backup directory nearly full"],
  "errors": ["Signature verification failed for archive"],
  "data": {}
}
```

## Stability

- Command names and JSON schemas are versioned.
- Breaking changes require a major version bump.
- Non-breaking additions are allowed in minor versions.
- Deprecated commands emit warnings.

## Authentication

- The command API runs as the Termux user.
- Security-critical commands may require session gate re-authentication.
- No network listener exposes the API remotely.

## Examples

```bash
hive status --json
hive service list --json
hive agent run task.yaml --json
hive workspace create research --type research --json
```
