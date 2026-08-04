# Hermes Plugin Specification

## Design principle

The Hermes plugin is a thin, safe bridge. It does not become a second Hive control plane. It exposes a small set of tools that invoke the canonical `hive` CLI through structured arguments.

## Plugin location

```text
integrations/hermes/plugin/
├── __init__.py
├── manifest.yaml
├── tools/
│   ├── status.py
│   ├── doctor.py
│   ├── verify.py
│   ├── task_validate.py
│   ├── task_run.py
│   ├── agent_list.py
│   ├── agent_halt.py
│   └── emergency_stop.py
├── adapters/
│   └── cli_adapter.py
└── tests/
    └── (unit tests with mocked hive subprocess)
```

## Exposed tools

| Tool | Hive command | Purpose | Writable? |
|------|--------------|---------|-----------|
| `hive_status` | `hive status --json` | Read status | No |
| `hive_doctor` | `hive doctor --json` | Diagnostics | No |
| `hive_verify` | `hive verify --json` | Verify install | No |
| `hive_task_validate` | `hive agent validate-task TASK --json` | Validate task manifest | No |
| `hive_task_run` | `hive agent run TASK --json` | Run bounded task | Yes, within task scope |
| `hive_agent_list` | `hive agent list --json` | List agents | No |
| `hive_agent_halt` | `hive agent halt ID --json` | Halt agent | Yes (process stop) |
| `hive_emergency_stop` | `hive emergency-stop --json` | Stop all Hive processes | Yes (emergency) |

## Tool requirements

- Invoke `hive` with `--json` flag.
- Parse JSON output; fail closed on malformed output.
- Detect missing Hive installation and return a clear error.
- Validate Hive version compatibility at plugin load.
- Time out after a configured maximum (default 30 seconds).
- Never crash the Hermes agent loop on plugin failure.
- Never expose vault contents.
- Never write to Hermes memory or sessions.
- Never start network services automatically.
- Never edit Hermes core.

## Manifest format

```yaml
name: hive-hermes-adapter
version: 1.0.0
entry_point: __init__.py
register_tools:
  - hive_status
  - hive_doctor
  - hive_verify
  - hive_task_validate
  - hive_task_run
  - hive_agent_list
  - hive_agent_halt
  - hive_emergency_stop
requires:
  python: ">=3.11"
  hermes: ">=1.0"
```

## Installation into Hermes

The plugin is installed into the active Hermes profile's `~/.hermes/plugins/hive-hermes-adapter/` directory. It is discovered by Hermes plugin loading; no core files are copied or modified.

## Error handling

- Subprocess failure → return structured error dict with exit code and stderr excerpt.
- Missing `hive` binary → return error instructing user to install Hive OS.
- Version mismatch → return error with expected and actual versions.
- Timeout → return error with partial output.

## Test strategy

Unit tests use a mocked `hive` subprocess. Each tool test verifies:
- Correct CLI args are generated.
- Valid JSON is parsed.
- Malformed output fails closed.
- Missing binary is handled.
