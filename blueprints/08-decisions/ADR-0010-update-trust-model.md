# ADR-0010: Update Trust Model

## Status

Proposed.

## Context

Current update uses raw `git pull` with no verification. This is unsafe.

## Decision

The initial secure update path uses staged, signed release archives with cryptographic digest verification. A raw `git pull` remains available as a development-only option but is never described as secure.

Trust levels:
- DEVELOPMENT GIT UPDATE (internal only).
- SIGNED RELEASE UPDATE (primary).
- OFFLINE VERIFIED BUNDLE (supported).
- EMERGENCY RECOVERY BUNDLE (future).

## Consequences

- Users download a specific release, verify digest/signature, then apply.
- Rollback point is retained.
- Update journal is maintained.

## Rejected alternatives

- Raw `git pull` as secure update — rejected.
