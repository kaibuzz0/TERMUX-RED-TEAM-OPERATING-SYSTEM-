# Hermes Integration Map

## Current Integration Artifacts

| Path | Role | Status |
|------|------|--------|
| `Hermes Plugins/install.sh` | Copies a plugin skeleton into `~/.hermes/plugins/hive-ops-plugin/` | Prototype installer |
| `Hermes Plugins/hive-ops-plugin/__init__.py` | Plugin registration stub | Uninspected head |
| `Hermes Plugins/hive-ops-plugin/brain_plug.py` | Brain-Plug adapter for Hermes | Uninspected head |
| `Hermes Plugins/hive-ops-plugin/agents/__init__.py` | Agent package stub | Uninspected head |
| `install.sh` | Writes `HERMES_HIVE_MODE="assist"` and `HERMES_HIVE_BRIDGE="$HIVE_SHARED/bridge.sock"` to `~/.config/hive/env.sh` | Legacy installer bridge |
| `Hive Ops DevAI/bin/hive-hermes` | DevAI Hermes bridge command | Listed in inventory; head not yet read |

## What the current integration attempts

- The `install.sh` installer sets two environment variables that suggest a Unix-socket bridge between Hive and Hermes.
- The `Hermes Plugins/hive-ops-plugin/` directory is a minimal plugin skeleton that copies files into `~/.hermes/plugins/` but does not appear to register Hermes tools/skills through the documented `ctx.register_tool(...)` / `ctx.register_cli_command(...)` API.
- There is no evidence yet of a Hermes skill package for Hive OS under the repo's `skills/` directory.
- The `brain-plug/` module is a standalone Flask/NLP tool; it is not wired into Hermes through the plugin skeleton in a way visible from the inventory.

## Gaps vs. intended architecture

The directive calls for:

```text
integrations/hermes/
 plugin/
    __init__.py
    manifest.yaml
    tools/
    policy/
    adapters/
    tests/
 skills/
    hive-architect/
    hive-auditor/
    hive-builder/
    hive-tester/
    hive-release-verifier/
 profiles/
    architect.yaml
    auditor.yaml
    builder.yaml
    reviewer.yaml
 docs/
```

Current repo has none of this. The Hermes integration is at **prototype/skeleton** level.

## Evidence

- Path: `Hermes Plugins/install.sh` lines 38-68
- Observation: copies `__init__.py`, `brain_plug.py`, `agents/__init__.py`, writes `plugin.json` with capabilities list but no tool schemas.
- Confidence: HIGH

- Path: `install.sh` lines ~145-165
- Observation: writes `HERMES_HIVE_MODE` and `HERMES_HIVE_BRIDGE` env vars.
- Confidence: MEDIUM (not yet fully read)

## Security note

- Copying files into `~/.hermes/plugins/` as `install.sh` does is a legitimate Hermes plugin surface, but the plugin code has not been audited for what hooks/tools it registers.
- No `check_fn` or gated tool registration was observed in the installer head.
