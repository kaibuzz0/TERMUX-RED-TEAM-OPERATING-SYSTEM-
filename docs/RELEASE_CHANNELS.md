# Release Channels

Channels:

- `stable` (default)
- `beta`
- `development`

Rules:

- stable cannot install beta/development
- beta cannot install development
- channel switch is explicit and auditable
- anti-rollback applies across channels
