# Resource Management Specification

## Constraints

Hive OS targets normal Android phones with limited memory, storage, and battery.

## Defaults

- No persistent background services by default.
- No default background agents.
- No default public listeners.
- No continuous scanning.
- No heavy databases by default.
- No Chromium automation by default.
- No large local LLMs by default.

## Resource budgets (targets, not measured claims)

| Operation | Target budget |
|-----------|---------------|
| `hive status` warm | < 500 ms |
| `hive status` cold | < 1.5 s |
| `hive doctor` (no network) | < 5 s |
| Idle supervisor RSS | < 50 MB where achievable |
| Workspace creation (no PRoot) | < 3 s |
| Workspace creation (with existing PRoot image) | < 15 s |
| Emergency stop begin | < 1 s |
| Emergency stop complete (cooperative) | < 10 s |
| Log storage | Bounded by retention + size limit |

## Battery and thermal

- Optional wake-lock only for explicitly enabled services.
- Services may have run-while-charging policy.
- Thermal throttling is handled by Android; Hive should not fight it.
- Long-running tasks should checkpoint progress.

## Process limits

- `max_processes` per agent task.
- Service supervisor crash-loop cutoff.
- Workspace process tracking.

## Storage management

- Cache directories bounded by size.
- Old backups rotated.
- Logs compressed after retention period.
- Operator can run `hive doctor --storage` for cleanup suggestions.

## Measurement

These budgets must be measured on a reference Android device before claiming them as guarantees.
