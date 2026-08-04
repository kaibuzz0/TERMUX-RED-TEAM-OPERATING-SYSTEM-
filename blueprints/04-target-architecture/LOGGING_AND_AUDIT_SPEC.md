# Logging and Audit Specification

## Log categories

| Category | Location | Retention |
|----------|----------|-----------|
| Agent log | `~/.local/share/hive/logs/agent/YYYY-MM-DD/` | 30 days |
| Service log | `~/.local/share/hive/logs/services/NAME/` | Configurable |
| Command log | `~/.local/share/hive/logs/commands/YYYY-MM.log` | 30 days |
| Audit log | `~/.local/share/hive/audit/YYYY-MM.log` | Configurable |

## Audit events

The audit log records security-relevant state transitions:

- Login/lockout/session-gate events.
- Service start/stop.
- Workspace create/destroy/enter.
- Agent task run/halt.
- Vault lock/unlock (no secret values).
- Update stage/apply/rollback.
- Recovery level invocation.
- Backup create/verify/restore.
- Network listener changes.
- Policy denials.

## Redaction

The audit logger must redact:

- Passwords and PINs.
- API keys and tokens.
- Vault plaintext.
- Private keys.
- Clipboard contents.
- Sensitive file contents.

## Format

JSON Lines:

```json
{
  "timestamp": "2026-08-03T12:00:00Z",
  "event": "vault.unlock",
  "actor": "operator",
  "outcome": "success",
  "details": {"vault_id": "..."}
}
```

## Integrity

- Append-only files.
- SHA-256 hash chain per log file.
- Optional remote sealing.
- Tamper detection on verify.

## Retention and rotation

- Monthly log files.
- Configurable retention.
- Old logs may be compressed.
- Operator-visible log status via `hive audit`.
