# ADR-0002: Hermes Integration Boundary

## Status

Proposed.

## Context

Hive OS wants to leverage Hermes as its control system without becoming a fork of Hermes or modifying Hermes core.

## Decision

Use the extension order:

1. Project context files (this repo).
2. Hermes skills for Hive OS (`integrations/hermes/skills/`).
3. Hermes user profiles for Hive roles (`integrations/hermes/profiles/`).
4. Hermes user plugin for runtime tools (`integrations/hermes/plugin/`).
5. MCP adapters for external capabilities.
6. External command adapters.
7. Upstream-compatible Hermes contribution (only if generic).
8. Hermes core modification — **last resort only**, only if unavoidable and approved.

## Boundary rules

- Hive code belongs in this repo.
- Hermes configuration, plugins, skills, and profiles belong in `~/.hermes/` at runtime, sourced from `integrations/hermes/` in this repo.
- Never copy Hermes core files into this repo.
- Never modify `agent/conversation_loop.py`, `agent/tool_executor.py`, `agent/prompt_builder.py`, `agent/context_compressor.py`, `gateway/run.py`, `tools/terminal_tool.py`, or `tools/approval.py` from this project.

## State sharing

- Hive may read Hermes configuration for integration purposes.
- Hive must not write to Hermes memory or sessions without explicit user opt-in.
- Hermes may invoke Hive via the canonical `hive` CLI or the plugin's registered tools.

## Emergency stop

- Hermes plugin must implement a `hive emergency-stop` tool that terminates any running Hive-managed background processes.
- Plugin failure must be contained: a broken plugin must not crash the Hermes agent loop.
