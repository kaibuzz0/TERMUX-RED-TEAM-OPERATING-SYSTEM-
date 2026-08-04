# ADR-0011: Recovery Model

## Status

Proposed.

## Context

Current `emergency-repair.sh` is destructive and lacks tiers.

## Decision

Replace with a tiered recovery system:
- Level 0 Diagnose
- Level 1 Repair links/permissions
- Level 2 Restore canonical runtime from local verified copy
- Level 3 Roll back last update
- Level 4 Reinstall runtime preserving config/data
- Level 5 Restore encrypted recovery bundle
- Level 6 Explicit destructive reset

Level 6 requires typed confirmation phrase, path validation, and backup offer.

## Consequences

- Operators can recover without losing data.
- Destructive reset is heavily guarded.

## Rejected alternatives

- Single "emergency repair" script with `rm -rf` — rejected as unsafe.
