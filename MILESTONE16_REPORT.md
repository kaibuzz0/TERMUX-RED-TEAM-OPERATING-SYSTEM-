# HIVE OS MILESTONE 16 REPORT

## Plugin / Extension SDK, Capability Contracts, Lifecycle, and Safe Extension Boundaries

**Status:** IN PROGRESS — not yet committed.

**Baseline:** Milestone 15 commit `e54feeb19794cdbe07f15499b67a4153534f992a`

### Plugin SDK

- SDK version: `1.0`
- Manifest schema version: `1`
- Package: `plugin_sdk/`

### Plugin Types

- `client`
- `collector`
- `renderer`
- `validator`

### Default State

`DISABLED`

### Capabilities

- Read-only grants only
- Mutating grants: `NO`
- Wildcard capability: `REJECTED`
- Shell capability: `REJECTED`

### Policy Integration

- Actor type: `future_plugin`
- Broker remains enforcement point
- Plugin cannot bypass Policy

### Configuration

- Authority: `config_engine`
- Namespace: `plugins.<plugin_id>`
- Secrets in config: `REDACTED`

### Lifecycle

- Validation executes code: `NO`
- Install planning executes code: `NO`
- Auto-enable: `NO`
- Auto-start: `NO`

### Execution Model

- Preferred: SDK + manifest architecture, trusted example plugins, read-only execution
- Isolation claim: broker/policy/process-level, not kernel containment
- Network default: `DENY`
- Vault secret access: `DENY`
- Failure containment: `YES`

### Signature Model

- Unsigned policy: production may deny
- Trust states: `UNSIGNED`, `SIGNED_UNTRUSTED`, `SIGNED_TRUSTED`, `INVALID_SIGNATURE`, `REVOKED`
- Private key in repository: `NO`

### Example Plugin

- `examples/plugins/hive-status/`
- Read-only, no network, no secrets, disabled by default

### Legacy Plugin

- `Hermes Plugins/hive-ops-plugin/`: `UNSUPPORTED / HIGH_RISK`
- Registered: `NO`
- Activated: `NO`

### Operations Center

- Read-only plugin view added
- Lifecycle mutation available: `NO`

### Verification

| Check | Result |
|---|---|
| `python -m pytest -q` | **483 passed, 8 skipped** |
| Plugin SDK tests | **58 passed** |
| Policy regression | **67 passed** |
| Broker regression | **25 passed** |
| Operations Center regression | **17 passed** |
| Static scans | **clean** (forbidden-capability/wildcard strings are schema deny-list definitions, not production usage) |
| `git diff --check` | **clean** |

### Files Created

- `plugin_sdk/`
- `examples/plugins/hive-status/`
- `tests/test_plugin_sdk_core.py`
- `tests/test_plugin_sdk_runtime.py`
- `tests/test_plugin_sdk_cli.py`
- `tests/fixtures/plugins/hive-status-example.zip`
- `docs/PLUGIN_*.md`
- `blueprints/implementation/milestone-16/`

### Files Modified

- `bin/hive` — added `plugin` subcommand delegation
- `operations_center/plugin_view.py` — new read-only plugin view

### Files Deferred

- `services/` — conditional, not required in Milestone 16

### Safety Declarations

- No arbitrary shell execution enabled.
- No network listeners opened.
- No Hermes core or skill modifications.
- No user data changed.
- No packages installed.
- No services started.
- Physical Termux validation deferred to Milestone 18.
- Milestone 17 not started.

### Recommended Milestone 17

Packaged plugin distribution and dependency resolution.
