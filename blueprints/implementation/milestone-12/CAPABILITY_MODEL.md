# Capability Model

The broker advertises a stable capability set. Clients discover capabilities with `hive broker capabilities` and request only those they need.

Capabilities are named with a `subsystem.action` pattern:
- `service.status`
- `service.health`
- `service.list`
- `vault.status`
- `update.status`
- `recovery.diagnose`
- `broker.stop`

Adding a new capability requires a broker version bump and explicit client opt-in.


## Versioning

- Additive backward-compatible capability: same major broker version allowed.
- Capability removal: major version bump required.
- Semantic behavior change: major version bump required.
- Clients must explicitly request every required capability.
- Capability names must never silently change meaning.
