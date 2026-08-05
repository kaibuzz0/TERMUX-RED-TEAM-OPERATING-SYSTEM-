# HIVE OS MILESTONE 13 ARCHITECTURE PLAN
## Operations Center

## Goal

Create a single read-only operational entry point for administrators that surfaces the runtime, services, updates, recovery, vault, broker, and diagnostics subsystems. Every view must route through the broker with observer policy; no subsystem is accessed directly.

## Guiding principle

> Milestone 13 makes the existing subsystems feel like one operating system.

## Components

### 1. Operations Center package (`operations_center/`)

```
operations_center/
    __init__.py
    schema.py             # view/output schemas
    data_sources.py       # broker-backed collectors
    views.py              # assemble views
    render.py             # human-readable formatting
    cli.py                # `hive ops` command
    errors.py
```

### 2. CLI-first approach

Milestone 13 implements a terminal Operations Center via:

```
hive ops              # show System Overview
hive ops services     # service status and dependencies
hive ops updates      # update state and rollback points
hive ops recovery     # recovery tiers and diagnostics
hive ops vault        # vault metadata (no secrets)
hive ops broker       # active sessions, transactions, capabilities
hive ops diagnostics  # event timeline and warnings
```

### 3. Data sources

Each view collects data by submitting read-only task manifests to the broker:

- `service.list`, `service.status`, `service.health`, `service.graph`
- `update.status`, `update.inspect`, `update.plan`
- `recovery.status`, `recovery.diagnose`
- `vault.status`
- `broker.status`, `broker.capabilities`

### 4. View model

Each command returns a stable JSON output plus an optional human-readable summary.

Example System Overview:

```json
{
  "schema_version": 1,
  "runtime": {"platform": "...", "version": "..."},
  "health": {"status": "ok", "services_running": 0, "services_failed": 0},
  "version": {"current": "fc13e2f", "pending": null},
  "broker": {"session_id": "...", "active_transactions": 0},
  "vault": {"state": "locked"},
  "diagnostics": {"warnings": 0, "errors": 0}
}
```

### 5. Safety rules

- Only read-only broker capabilities are used.
- No mutating actions in any view.
- No shell command rendering.
- No secret display.
- No direct file reads outside broker mediation.
- No automatic refresh that triggers service starts.
- No network calls.

## Files expected

New:
- `operations_center/` (8 files)
- `tests/test_operations_center.py`
- `tests/fixtures/operations_center/`
- `docs/OPERATIONS_CENTER.md`
- `docs/OPERATIONS_CENTER_VIEWS.md`
- `blueprints/implementation/milestone-13/OPERATIONS_CENTER_ARCHITECTURE.md`
- `blueprints/implementation/milestone-13/VIEW_MODEL.md`
- `blueprints/implementation/milestone-13/DATA_SOURCES.md`
- `blueprints/implementation/milestone-13/RENDERING.md`
- `blueprints/implementation/milestone-13/MILESTONE13_ACCEPTANCE.md`
- `MILESTONE13_REPORT.md`

Modified:
- `bin/hive` — add `ops` subcommand delegation
- `hive_broker/capabilities.py` — optionally add `ops.*` read-only capabilities

Not touched:
- Hermes core/skills
- Service supervisor internals
- Vault secret operations
- Update signing/recovery mutation
- Legacy plugin

## Acceptance criteria

- `hive ops` and subcommands produce stable JSON.
- All views use broker manifests with observer policy.
- No mutating actions.
- No secret leakage.
- No shell access.
- No service auto-start.
- All tests pass.
- Static scans clean.
