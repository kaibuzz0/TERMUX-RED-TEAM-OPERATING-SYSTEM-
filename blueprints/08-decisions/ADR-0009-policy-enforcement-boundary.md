# ADR-0009: Policy Enforcement Boundary

## Status

Proposed.

## Context

Hive OS must not claim to enforce global device security from ordinary Termux.

## Decision

Every target control is classified:
- BROKER-ENFORCED — Hive owns the dispatch path.
- FILESYSTEM-CONVENTION — directory/permission conventions.
- ADVISORY — Hive requests/validates but cannot prevent same-UID bypass.
- PROOT-COMPATIBILITY — optional PRoot enhancement.
- ROOT-ENHANCED — requires root.
- FUTURE RESEARCH — not available on standard Termux.

Standard Hive OS uses only BROKER-ENFORCED, FILESYSTEM-CONVENTION, and ADVISORY controls.

## Consequences

- Honest product claims.
- Clear separation of optional features.
- No kernel isolation promises.

## Rejected alternatives

- Claiming seccomp/Landlock/SELinux for standard Termux — rejected because availability is not guaranteed.
