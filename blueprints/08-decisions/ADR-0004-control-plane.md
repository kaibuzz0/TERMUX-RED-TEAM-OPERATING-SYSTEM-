# ADR-0004: Control Plane

## Status

Proposed.

## Context

Hive OS needs one user-facing command surface to avoid divergence between CLI, TUI, and Hermes plugin.

## Decision

The canonical command is `hive`. All user-facing operations are reachable through `hive` or explicitly labeled as low-level compatibility commands. The TUI is a client of the `hive --json` API.

## Consequences

- Single command registry.
- Consistent exit codes and JSON schemas.
- TUI and Hermes plugin share the same backend.

## Rejected alternatives

- Multiple CLIs (`hive`, `hive-os`, `hive-ctrl`) — causes confusion.
- TUI as independent implementation — duplicates business logic.
