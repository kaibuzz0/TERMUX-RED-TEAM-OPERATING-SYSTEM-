# HIVE OS MILESTONE 12 ARCHITECTURE PLAN

## Goal

Provide a controlled, opt-in integration between Hive OS and Hermes Agent that lets a user delegate bounded tasks to Hive services without giving Hermes arbitrary shell access or automatic service control.

## Core components

### 1. Broker module (`hive_broker/`)

A narrow Python package living inside Hive OS:

```
hive_broker/
    __init__.py
    schema.py        # task manifest schema
    validator.py     # permission and safety validation
    dispatcher.py    # dispatch to services / tools / vault (read-only where appropriate)
    session.py       # per-conversation session state
    stop.py          # emergency stop
    audit.py         # structured audit log
    cli.py           # `hive broker *` commands
    errors.py
```

### 2. Task manifest schema

Every delegated task must be represented by a validated manifest:

```json
{
  "schema_version": 1,
  "task_id": "uuid",
  "requestor": "hermes",
  "intent": "inspect-service-status",
  "allowed_actions": ["service.status", "service.health"],
  "target_services": ["fixture-http"],
  "target_paths": [],
  "read_only": true,
  "timeout_seconds": 30,
  "allowed_since_commit": "dab6618",
  "audit_level": "normal"
}
```

Unknown intents, unknown actions, or paths outside approved bases fail closed.

### 3. Permission model

Actions are whitelisted, not blacklisted:

- `service.status`
- `service.health`
- `service.list`
- `service.show`
- `service.validate`
- `service.graph`
- `vault.status` (no secret access)
- `update.status`
- `recovery.diagnose` (non-mutating)
- `broker.stop`

Mutating actions (`service.start`, `service.stop`, `update.apply`, `recovery.restore`) require an explicit two-step approval with a signed or operator-confirmed manifest.

### 4. Bounded agent integration

Two supported modes:

1. **Plugin mode** (future): a Hermes plugin calls the broker via `hive broker run --manifest FILE`. The plugin itself contains no Hive logic; it only translates user requests into manifests and passes them to the broker.
2. **CLI mode** (current): user can run `hive broker run --manifest FILE` manually. Hermes may suggest the manifest but never executes it without user confirmation.

### 5. Version compatibility

The broker validates that the running Hive OS commit is at or after the manifest's `allowed_since_commit`. Manifests referencing an older or unknown commit fail closed.

### 6. Emergency stop

- `hive broker stop` immediately cancels any in-progress broker task and resets broker session state.
- The broker records the stop event in the audit log.
- A stop token file under `STATE_ROOT` can also be checked by long-running tasks.

### 7. Workspace-aware execution

All file paths referenced by tasks are resolved through `lib/hive_path.py`. Manifests cannot reference arbitrary absolute paths or escape approved bases.

### 8. Audit log

Every broker action writes a JSON line to `LOG_ROOT/broker/audit.logl`:
- timestamp
- task_id
- intent
- result
- user confirmation status
- errors

No secrets, no environment dumps.


## Capability negotiation

The broker exposes a capability set to its clients. Example:

```json
{
  "broker_version": 1,
  "capabilities": [
    "service.status",
    "service.health",
    "service.list",
    "service.show",
    "service.validate",
    "service.graph",
    "vault.status",
    "update.status",
    "recovery.diagnose",
    "broker.stop"
  ]
}
```

A task manifest declares required capabilities:

```json
{
  "required_capabilities": ["service.status", "vault.status"]
}
```

The broker rejects manifests that require capabilities it does not advertise.
This decouples manifests from Git commits and supports forward compatibility.

The capability set is discoverable via:

```
hive broker capabilities
```

## Transaction IDs

Every broker request receives a unique transaction identifier:

```json
{
  "transaction_id": "txn-uuid",
  "task_id": "task-uuid",
  "session_id": "session-uuid",
  "audit_id": "audit-uuid"
}
```

The same `transaction_id` is propagated to services, updates, vault, and recovery subsystems so logs can be correlated across the platform.

IDs are generated on the broker side; clients may supply a `task_id` but never the `transaction_id`.

## Future direction (not in Milestone 12)

A local RPC interface may eventually replace the manifest-CLI flow:

```
Hermes → Hive Broker → Services / Vault / Updates / Recovery
```

That evolution preserves the same permission model and is intentionally deferred until the broker is mature.

## Files expected

New:
- `hive_broker/` (8 files)
- `tests/test_hive_broker_*.py`
- `tests/fixtures/broker/`
- `docs/HIVE_BROKER.md`
- `docs/HIVE_BROKER_TASK_MANIFEST.md`
- `docs/HIVE_BROKER_PERMISSIONS.md`
- `docs/HIVE_BROKER_AUDIT.md`
- `blueprints/implementation/milestone-12/BROKER_ARCHITECTURE.md`
- `blueprints/implementation/milestone-12/PERMISSION_MODEL.md`
- `blueprints/implementation/milestone-12/EMERGENCY_STOP.md`
- `blueprints/implementation/milestone-12/VERSION_COMPATIBILITY.md`
- `MILESTONE12_REPORT.md`

Modified:
- `bin/hive` — add `broker` subcommand delegation
- `services/supervisor.py` — optional narrow read-only status export
- `installer/` — optional registration hook (if required)

Not touched:
- Hermes Agent core or skills
- `gateway/`, `dashboard/`, `orchestrator/` (do not exist in repo)
- Vault internals
- Update signing
- Recovery policy
- Legacy `.svc` system
- Termux:Boot

## Acceptance criteria

- Broker rejects unknown intents and actions.
- Broker rejects manifests targeting paths outside approved bases.
- Mutating actions require explicit confirmation.
- Emergency stop works from CLI.
- Version compatibility check passes for current commit and fails for fabricated older commit.
- No Hermes core code changed.
- No service starts automatically.
- No shell tool exposed to Hermes.
- All tests pass (target baseline: 285+)
- Static scans clean.
