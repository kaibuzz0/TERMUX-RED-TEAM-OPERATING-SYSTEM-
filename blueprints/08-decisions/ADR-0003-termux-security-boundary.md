# ADR-0003: Termux Security Boundary

## Status

Proposed.

## Context

Hive OS runs on standard Android Termux. It must not claim security capabilities that Termux cannot provide.

## Decision

Standard Hive OS provides only user-space policy:

- Safe command dispatch.
- File-permission discipline.
- Encrypted application data (Android-provided).
- Workspace organization.
- Process supervision.
- Local-only services.
- Scoped agent permissions.
- Integrity checking.
- Transactional application updates.
- Backup and recovery.
- Auditing.

## Explicitly unsupported capabilities

The following are **not** provided by standard Hive OS and must be classified separately:

- Android kernel replacement.
- Verified boot control.
- Android lock-screen replacement.
- SELinux policy enforcement.
- VM-level isolation.
- Full isolation between same-UID processes.
- Guaranteed persistent background execution.
- Global network firewall authority.

## Classification labels

Every feature must be labeled:

- `STANDARD` — works on non-root Termux.
- `ROOT-ENHANCED` — requires root.
- `CUSTOM-ROM` — requires modified Android image.
- `HARDWARE-DEPENDENT` — requires specific device.
- `FUTURE RESEARCH` — not yet implemented.

## Consequences

- README and UI must use accurate terminology: "Hive session lock" instead of "boot authentication".
- Workspace isolation must be described as organizational/policy-based, not kernel-enforced.
- Root-enhanced modules must be optional and disabled by default.
