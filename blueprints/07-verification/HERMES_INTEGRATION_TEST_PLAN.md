# Hermes Integration Test Plan

## Plugin tests (mocked)

- Each tool invokes correct `hive --json` command.
- Malformed `hive` output fails closed.
- Missing `hive` binary returns clear error.
- Plugin load validates version compatibility.
- Plugin failure does not crash Hermes agent loop.

## Skill tests

- `hive-architect` skill can read repo and produce ADRs.
- `hive-auditor` skill can run static scans and write reports.
- `hive-builder` skill can only modify approved paths.
- `hive-reviewer` skill can read diffs and write findings.

## Profile tests

- Each profile has isolated memory/sessions.
- Profile-specific toolsets are enforced.
- Cross-profile state leakage is prevented.
