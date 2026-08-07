# Plugin Security

Plugins are the most dangerous extension surface. Milestone 16 treats every plugin as a potential adversary.

## Boundaries

- No shell access.
- No arbitrary subprocess strings.
- No network access by default.
- No vault secret access.
- No direct policy modification.
- No direct config file parsing.
- No global config writes.
- No auto-execution at install time.
- No auto-enable.
- No public listeners.

## Isolation

Isolation is broker/policy/process-level, not kernel containment. Standard Termux cannot provide strong same-UID sandboxing.

## Failure Containment

Malformed manifests, incompatible plugins, policy denials, timeouts, and crashes are contained. Hive core health is protected.
