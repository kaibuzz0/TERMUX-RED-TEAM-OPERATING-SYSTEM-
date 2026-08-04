# TUI Specification

## Design principle

The TUI is a **client** of the stable `hive` command API. It does not duplicate business logic.

## Architecture

```text
TUI process
    → runs `hive <command> --json`
    → parses JSON output
    → renders UI
    → sends user input back as CLI args
```

## TUI binary

`core/bin/hive-tui` may be launched directly, but all operations go through `hive`.

## View requirements

- Status dashboard: CPU, memory, network, service states.
- Command palette: search and run `hive` commands.
- Workspace browser.
- Service monitor.
- Agent monitor.
- Log viewer (tail Hive logs).
- Audit viewer (secret-redacted).

## Security indicators

- Display current platform profile.
- Display vault lock state.
- Display whether any service is bound to non-loopback.
- Display active workspaces and their types.

## Fallback

If TUI fails, the operator can always use the CLI. The TUI must not be required for any operation.
