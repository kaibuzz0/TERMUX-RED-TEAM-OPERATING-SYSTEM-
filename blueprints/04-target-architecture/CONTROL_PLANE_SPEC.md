# Control Plane Specification

## Canonical command

```text
hive [GLOBAL_OPTIONS] COMMAND [SUBCOMMAND] [ARGS]
```

All user-facing operations are reachable through `hive` unless explicitly labeled as a low-level compatibility command.

## Global options

| Option | Purpose |
|--------|---------|
| `--json` | Emit structured JSON output |
| `--dry-run` | Preview mutations without executing |
| `--yes` / `--no` | Non-interactive confirmation |
| `--profile NAME` | Use a platform profile |
| `--config PATH` | Override config file |
| `--log-level LEVEL` | Adjust verbosity |
| `--diagnose` | Run self-diagnostics |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Config validation failed |
| 4 | State locked or unavailable |
| 5 | Service unavailable |
| 6 | Network unavailable or blocked |
| 7 | Vault locked or corrupt |
| 8 | Update/repair verification failed |
| 9 | Agent task rejected or failed |
| 10 | Emergency stop triggered |
| 11 | Platform capability missing |
| 20 | Operator cancelled |

## Command catalog (target)

| Command | Purpose | Release milestone |
|---------|---------|-------------------|
| `hive status` | System status | M1 |
| `hive doctor` | Environment diagnostics | M1 |
| `hive verify` | Verify installation integrity | M1 |
| `hive config show` | Show merged config | M1 |
| `hive config validate` | Validate config files | M1 |
| `hive config diff` | Show config changes | M2 |
| `hive system info` | Platform and capability info | M1 |
| `hive system health` | Health check | M1 |
| `hive system profile` | Show active profile | M1 |
| `hive service list` | List managed services | M3 |
| `hive service status NAME` | Service status | M3 |
| `hive service start NAME` | Start service | M3 |
| `hive service stop NAME` | Stop service | M3 |
| `hive service restart NAME` | Restart service | M3 |
| `hive workspace list` | List workspaces | M2 |
| `hive workspace create NAME` | Create workspace | M2 |
| `hive workspace enter NAME` | Enter workspace shell | M2 |
| `hive workspace destroy NAME` | Destroy workspace | M2 |
| `hive workspace export NAME` | Export workspace artifact | M2 |
| `hive agent list` | List running agents | M4 |
| `hive agent inspect ID` | Agent task manifest | M4 |
| `hive agent run TASK` | Run bounded agent task | M4 |
| `hive agent halt ID` | Halt agent | M4 |
| `hive agent halt --all` | Halt all agents | M4 |
| `hive hermes status` | Hermes plugin/adapter status | M5 |
| `hive hermes verify` | Verify Hermes integration | M5 |
| `hive hermes profile list` | List Hermes profiles | M5 |
| `hive hermes task validate TASK` | Validate task manifest | M5 |
| `hive vault status` | Vault status | M4 |
| `hive vault lock` | Lock vault | M4 |
| `hive vault unlock` | Unlock vault | M4 |
| `hive vault audit` | Vault access log | M4 |
| `hive network status` | Network status | M2 |
| `hive network listeners` | List listeners | M2 |
| `hive network kill` | Stop Hive-managed listeners | M2 |
| `hive backup create` | Create backup | M3 |
| `hive backup verify` | Verify backup | M3 |
| `hive backup restore --preview` | Preview restore | M3 |
| `hive update check` | Check for updates | M6 |
| `hive update stage` | Stage update | M6 |
| `hive update apply` | Apply staged update | M6 |
| `hive update rollback` | Rollback update | M6 |
| `hive recovery diagnose` | Recovery diagnostics | M6 |
| `hive recovery repair` | Tiered repair | M6 |
| `hive recovery rollback` | Rollback to previous version | M6 |
| `hive audit` | Show audit log | M3 |
| `hive logs` | Show Hive logs | M3 |
| `hive emergency-stop` | Stop all Hive-managed processes | M3 |

## JSON output schema (common envelope)

```json
{
  "command": "hive status",
  "success": true,
  "exit_code": 0,
  "timestamp": "2026-08-03T12:00:00Z",
  "platform_profile": "termux-standard",
  "data": { ... }
}
```

## Mutation classification

| Class | Examples | Behavior |
|-------|----------|----------|
| Read-only | `status`, `doctor`, `config show` | No confirmation needed |
| State mutation | `service start`, `workspace create` | Dry-run available; confirmation optional |
| Destructive | `workspace destroy`, `recovery repair` | Confirmation required unless `--yes` |
| Security-critical | `vault unlock`, `update apply` | May require session gate re-authentication |

## Approval requirements

| Operation | Approval | Lock | Log event |
|-----------|----------|------|-----------|
| `update apply` | Explicit `--yes` or interactive | Update lock | `update.apply` |
| `recovery repair` | Interactive + typed confirmation phrase | Recovery lock | `recovery.repair` |
| `workspace destroy` | Interactive unless `--yes` | Workspace lock | `workspace.destroy` |
| `agent run` | Task manifest pre-validation | Agent lock | `agent.run` |
| `emergency-stop` | No approval; always available | None | `emergency.stop` |
| `vault unlock` | Session gate passphrase | None | `vault.unlock` (no secret) |

## Secret exposure risk

- No command accepts secrets on the command line.
- Secrets are read from the vault or prompted interactively.
- Audit log records events, never secret values.

## Standard-Termux availability

Every command is labeled with standard-Termux availability in the command catalog above. All M1-M6 milestones target standard Termux unless marked root-enhanced.

## Dry-run and idempotency

- Destructive commands support `--dry-run`.
- Read-only commands are idempotent.
- State-mutating commands are idempotent where feasible (e.g., `service start` on already-started service returns success).
- Update/repair operations are not idempotent by nature but produce rollback points.
