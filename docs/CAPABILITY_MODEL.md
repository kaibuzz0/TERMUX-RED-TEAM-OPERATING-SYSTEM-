# Hive OS Capability Model

**Version:** 1.1  
**Status:** Pass F — Broker / Policy / Operations Center Integration

---

## Architecture

```text
Hermes / Agent
      │
      ▼
  Hive Broker
      │
      ▼
Policy Engine
      │
      ▼
READ-ONLY by default; mutating only after explicit policy approval
      │
      ▼
   Network      Services    Diagnostics    Logs    Termux    Vault    Update    Recovery
```

The broker reduces agent authority.  There is no unrestricted shell or
arbitrary command execution capability.

---

## Capability Table

| Capability | Category | read_only | approval | Notes |
|------------|----------|-----------|----------|-------|
| `network.status` | network | yes | none | Pass B network manager |
| `network.health` | network | yes | none | Pass B health aggregator |
| `network.profile.read` | network | yes | none | Current profile |
| `service.list` | services | yes | none | Pass C registry |
| `service.show` | services | yes | none | Pass C supervisor |
| `service.status` | services | yes | none | Pass C supervisor |
| `service.health` | services | yes | none | Pass C health checks |
| `service.validate` | services | yes | none | Dependency graph |
| `service.graph` | services | yes | none | Service graph |
| `diagnostics.health` | diagnostics | yes | none | `hive health` |
| `diagnostics.doctor` | diagnostics | yes | none | `hive doctor` |
| `diagnostics.audit` | diagnostics | yes | none | `hive audit` |
| `logs.status` | logging | yes | none | runtime_logs overview |
| `logs.tail` | logging | yes | none | Bounded tail |
| `logs.service.read` | logging | yes | none | Known service log |
| `termux.integration.status` | termux | yes | none | Autoboot/launcher status |
| `vault.status` | vault | yes | none | Vault locked/unlocked |
| `update.status` | update | yes | none | Update state |
| `update.inspect` | update | yes | none | Inspect staged bundle |
| `update.plan` | update | yes | none | Plan update |
| `update.verify` | update | yes | none | Verify signatures |
| `recovery.status` | recovery | yes | none | Recovery journal state |
| `recovery.diagnose` | recovery | yes | none | Recovery diagnostics |
| `broker.capabilities` | broker | yes | none | Capability catalog |
| `broker.status` | broker | yes | none | Broker session status |
| `policy.status` | policy | yes | none | Policy engine status |
| `policy.profiles` | policy | yes | none | Available profiles |
| `policy.explain` | policy | yes | policy | Explain policy decision |

### Mutating capabilities (not advertised by default)

| Capability | Category | read_only | approval | Notes |
|------------|----------|-----------|----------|-------|
| `network.profile.change` | network | no | policy+manual | Reserved, not advertised |
| `network.identity.renew` | network | no | policy+manual | Reserved, not advertised |
| `service.start` | services | no | policy+manual | Reserved, not advertised |
| `service.stop` | services | no | policy+manual | Reserved, not advertised |
| `service.restart` | services | no | policy+manual | Reserved, not advertised |
| `logs.rotate` | logging | no | policy+manual | Reserved, not advertised |
| `diagnostics.selftest` | diagnostics | no | policy+manual | Reserved, not advertised |

---

## Policy Identities

| Policy identity | Maps to capabilities |
|-----------------|------------------------|
| `network.read` | network.status, network.health, network.profile.read |
| `network.change` | network.profile.change, network.identity.renew |
| `service.read` | service.list, service.show, service.status, service.health, service.graph, service.validate |
| `service.control` | service.start, service.stop, service.restart |
| `diagnostics.read` | diagnostics.health, diagnostics.doctor, diagnostics.audit |
| `diagnostics.active_test` | diagnostics.selftest |
| `logs.read` | logs.status, logs.tail, logs.service.read |
| `logs.rotate` | logs.rotate |
| `termux.read` | termux.integration.status |
| `termux.repair` | termux integration mutation (reserved) |
| `vault.status` | vault.status |
| `vault.use` | vault unlocking / secret use (reserved) |
| `update.read` | update.status, update.inspect, update.plan, update.verify |
| `broker.read` | broker.capabilities, broker.status |
| `policy.read` | policy.status, policy.profiles, policy.explain |

---

## Input / Output Contracts

Capabilities accept structured input and return structured JSON.

- `service.name` must match a registered Hive service.
- `network.profile` must be one of `direct`, `orbot`, `tor`, `hold`.
- `log.source` must be a registered service or runtime log identity.
- No path traversal.
- No shell fragments.

---

## Audit / Transactions

Every broker invocation receives a transaction ID.  Denials are logged in
the broker audit log.  No secrets are logged.

---

*See `docs/ORIGINAL_RUNTIME_PARITY.md` for command parity.*
*See `docs/NETWORK_MODEL.md`, `docs/SERVICE_SUPERVISOR.md`, `docs/DIAGNOSTICS_AND_LOGGING.md`, `docs/OPERATOR_EXPERIENCE.md`.*
