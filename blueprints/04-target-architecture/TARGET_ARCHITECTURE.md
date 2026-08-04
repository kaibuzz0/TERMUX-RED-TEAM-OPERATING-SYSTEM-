# Target Architecture

## Principles

1. **One control plane:** all operations reachable through `hive` CLI or explicitly labeled low-level compatibility commands.
2. **One canonical runtime tree:** `core/` eventually contains all production runtime code.
3. **No big-bang rewrite:** migration proceeds through small, reversible milestones.
4. **Android-first resource discipline:** no default persistent heavy services or listeners.
5. **Platform honesty:** standard Termux capabilities are separated from root/custom-ROM/hardware-dependent features.
6. **Broker-enforced vs advisory:** every control is classified by what Hive can actually enforce.

## High-level layers

```text
Operator
    ↓
Hive CLI / TUI client
    ↓
Control plane (dispatcher, config, state, audit, lock)
    ↓
Core services (service supervisor, workspace manager, agent broker, vault, network visibility)
    ↓
Hermes adapter / plugin
    ↓
Managed processes (tools, agents, services)
    ↓
Termux/Android runtime
```

## Canonical runtime tree (target)

```text
core/
├── bin/
│   ├── hive              # canonical CLI dispatcher
│   └── hive-tui          # TUI client (if launched directly)
├── lib/
│   ├── dispatcher.py
│   ├── config.py
│   ├── state.py
│   ├── audit.py
│   ├── lock.py
│   ├── shell_safe.py
│   ├── platform.py       # capability detection
│   ├── service_supervisor.py
│   ├── workspace.py
│   ├── agent_broker.py
│   ├── vault.py
│   ├── network.py
│   └── hermes_adapter.py
├── etc/
│   ├── env.sh
│   ├── shell-integration.sh
│   └── services.json
├── session-gate/
│   └── hive-session-gate.sh   # managed-session lock, NOT secure boot
├── services/
│   └── (service manifests)
├── tools/
│   └── (curated, audited tools)
└── _internal/
    └── (runtime generated state, never user-edited)
```

## Component responsibilities

| Component | Responsibility | Trust level |
|-----------|----------------|-------------|
| `hive` CLI dispatcher | Parse, validate, route commands | High |
| Configuration loader | Load, validate, merge configs | High |
| State manager | Read/write structured runtime state | High |
| Lock manager | Prevent concurrent destructive ops | High |
| Audit logger | Append-only, redacted event log | High |
| Capability detector | Identify platform tier and available controls | High |
| Service supervisor | Manage Hive-owned processes | High |
| Workspace manager | Create/destroy/enter managed contexts | Medium-High |
| Agent broker | Execute bounded task manifests | High |
| Vault | Encrypted secret storage | High |
| Network visibility module | Inspect and report listeners/routes | Medium |
| Hermes adapter | Safe plugin/tool bridge | Medium |
| TUI client | Visual client; no independent business logic | Medium |
| Compatibility layer | Old command aliases during migration | Low |

## Control classes

Every target control is classified as one of:

- **BROKER-ENFORCED:** Hive controls the operation because it owns the dispatch path.
- **FILESYSTEM-CONVENTION:** Enforced by directory/permission conventions; bypass possible by same-UID code.
- **ADVISORY:** Hive requests/validates but cannot prevent bypass by arbitrary same-UID code.
- **PROOT-COMPATIBILITY:** Enhanced when PRoot is configured.
- **ROOT-ENHANCED:** Requires rooted device.
- **FUTURE RESEARCH:** Not available on standard Termux.

## Language choices

| Component | Language | Justification |
|-----------|----------|---------------|
| CLI dispatcher, core runtime | Python 3 | Ubiquitous on Termux, rich stdlib, matches Hermes ecosystem |
| Shell integration, session gate | POSIX shell | Termux boot/shell init compatibility |
| Service manifests | JSON/YAML | Machine-readable, versioned, schema-validatable |
| TUI | Python with textual/rich | Python ecosystem, but TUI is a client only |
| Critical shell helpers | Python + small shell wrappers | Python gives safer path/argument handling |

Python is chosen not by preference but because the existing code and target environment are Python-centric, and Hermes is Python-based.

## Network defaults

- All Hive-managed services bind to loopback (`127.0.0.1` or Unix socket) by default.
- Remote binding requires explicit config flag and operator approval.
- Network visibility module lists all listening sockets on demand.
