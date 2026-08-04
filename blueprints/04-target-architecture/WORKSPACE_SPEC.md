# Workspace Specification

## Definition

A workspace is a **managed execution context**, not a VM or kernel sandbox. It provides:

- Dedicated directory.
- Explicit environment construction.
- Restricted PATH.
- Separate configuration.
- Separate caches and logs.
- Scoped vault references.
- Process tracking.
- Time and resource budgets.

## Control classification

| Mechanism | Class | Notes |
|-----------|-------|-------|
| Workspace directory isolation | FILESYSTEM-CONVENTION | Enforced by convention; bypass possible by same-UID code |
| Restricted PATH inside workspace | BROKER-ENFORCED | Only when entered through `hive workspace enter` |
| Scoped vault refs | BROKER-ENFORCED | Broker supplies capability, not raw secret |
| Process tracking | BROKER-ENFORCED | Tracks processes launched via Hive broker |
| Resource budgets | BROKER-ENFORCED | Limits applied to broker-managed processes |
| PRoot container | PROOT-COMPATIBILITY | Optional; requires PRoot image and configuration |
| Kernel isolation | FUTURE RESEARCH | Not available on standard Termux |

## Workspace types

| Type | Purpose | Risk level |
|------|---------|------------|
| `developer` | Normal coding, documentation, local testing | Low |
| `research` | Browsing, downloading papers, visiting unknown sites | Medium |
| `operations` | SSH, cloud consoles, deployment clients | Medium-High |
| `security-lab` | Authorized testing; requires explicit scope file | High |
| `forensics` | Incident response; read-only imports preferred | High |
| `ai-agent` | Bounded agent execution | Medium |
| `disposable` | One-off temporary context | Low |

## Security-lab scope file

A security-lab workspace must include an explicit authorization scope file:

```yaml
schema_version: 1
workspace_type: security-lab
authorization:
  operator_name: "..."
  target_allowlist:
    - "127.0.0.1"
  network_mode: deny-by-default
  allowed_tools:
    - scanner-x
  max_runtime_minutes: 60
  expiry: "2026-08-10T00:00:00Z"
```

Without a valid scope file, high-risk network functionality is disabled.

## Workspace lifecycle

```text
hive workspace create NAME --type TYPE
    → create directory structure
    → write workspace config
    → optionally stage PRoot image

hive workspace enter NAME
    → spawn subshell with workspace env/PATH
    → attach process tracking
    → apply resource budget

hive workspace destroy NAME
    → confirm destruction
    → terminate tracked processes
    → remove directory (or move to trash)

hive workspace export NAME
    → produce artifact bundle
    → record hashes
```

## File layout

```text
~/.local/share/hive/workspaces/NAME/
├── config.yaml
├── bin/
├── cache/
├── logs/
├── data/
├── vault-ref.yaml   # references, not secrets
└── scope.yaml       # for security-lab only
```

## Bypass limitations

Workspaces cannot prevent:
- A same-UID process from reading workspace files.
- The operator from opening a plain Termux shell and ignoring workspace boundaries.
- Android from killing the Termux process.

These limitations must be stated in user-facing documentation.
