# ADR-0008: Session Gate Terminology

## Status

Proposed.

## Context

The current code uses "secure login", "secure boot", and "boot authentication" for a Termux session prompt. These terms mislead users about the security provided.

## Decision

Use accurate terminology:
- `Hive session initialization`
- `Hive operator gate`
- `Hive shell access gate`
- `Termux session startup`
- `Hive managed-session lock`

The file path becomes `core/session-gate/hive-session-gate.sh`. It is a session-level lock, not Android device security.

## Consequences

- README and UI must avoid "secure boot" / "boot authentication" language.
- Users understand that another Termux session can bypass the gate.

## Rejected alternatives

- Keeping misleading terminology — rejected because it creates false security expectations.
