# Component Specifications

## Hive CLI dispatcher

| Attribute | Specification |
|-----------|---------------|
| Binary | `core/bin/hive` |
| Language | Python 3 |
| Entry | `__main__` dispatch |
| Trust level | High |
| State owned | Command history, current invocation |
| Files read | `core/etc/config.yaml`, user config, command registry |
| Files written | None (dispatches) |
| External commands | Spawns subcommands, services, tools |
| Network access | None directly |
| Secret access | None directly |
| Failure mode | Exit with documented code; do not mutate state on parse failure |
| Recovery | Re-run with `--help` or `--diagnose` |
| Resource budget | Under 50 MB cold start, under 500 ms warm |
| Public interface | CLI args, JSON output flag, exit codes |
| Security boundary | BROKER-ENFORCED for commands routed through it |
| Test strategy | Unit tests for every subcommand; schema tests for JSON output |

## Configuration loader

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/config.py` |
| Trust level | High |
| Files read | `core/etc/defaults.yaml`, `~/.config/hive/config.yaml`, env vars |
| Files written | None (read-only) |
| Validation | JSON schema; fail on unknown keys; warn on deprecated keys |
| Merging | Deep merge; user values override defaults |
| Secret access | Loads vault references, not secrets |
| Failure | Refuse to run if config is invalid; provide diagnostic message |
| Test | Validate against schema; test invalid configs |

## State manager

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/state.py` |
| Storage | `~/.local/share/hive/state.json` or SQLite |
| Trust level | High |
| Atomic writes | Write to temp file then rename |
| Backup | State changes appended to journal |
| Race | File locking via `portalocker` or atomic rename |
| Failure | Read-only fallback if state locked/corrupt |
| Test | Property tests for state transitions |

## Lock manager

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/lock.py` |
| Storage | `~/.local/share/hive/locks/` |
| Scope | Per-operation (update, repair, backup, agent run) |
| Timeout | Operations must declare max duration; stale locks detected |
| Failure | Refuse concurrent destructive operations; allow read-only overlap |
| Test | Simulate concurrent processes |

## Audit logger

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/audit.py` |
| Storage | `~/.local/share/hive/audit/YYYY-MM.log` |
| Format | JSON Lines: timestamp, event type, actor, outcome, redacted details |
| Redaction | Never log passwords, PINs, API keys, vault contents |
| Integrity | Append-only; checksums per file; optional remote sealing |
| Retention | Configurable; default 30 days |
| Test | Verify no secrets leak into audit records |

## Capability detector

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/platform.py` |
| Detects | Termux, root, Termux:API, PRoot, Python version, available packages |
| Output | Platform profile name and feature flags |
| Trust | ADVISORY for some detections (root can be hidden) |
| Test | Mock platform fixtures |

## Service supervisor

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/service_supervisor.py` |
| Manifest | `core/etc/services.json` |
| PID validation | Check PID exists and matches expected command line |
| Process-group tracking | Track process groups for cleanup |
| Restart | Exponential backoff; crash-loop cutoff |
| Shutdown | SIGTERM, then SIGKILL after grace period |
| Android death | Detect missing process on next invocation; optional wake lock |
| Log capture | Redirect stdout/stderr to log files |
| Test | Mock processes, simulate crashes |

## Workspace manager

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/workspace.py` |
| Root | `~/.local/share/hive/workspaces/` |
| Controls | Dedicated dir, env, PATH, cache, log, scoped vault refs |
| Class | Mostly BROKER-ENFORCED + FILESYSTEM-CONVENTION |
| Bypass | Same-UID code can ignore workspace boundaries |
| Test | Create/enter/destroy roundtrip |

## Agent broker

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/agent_broker.py` |
| Input | Declarative task manifest (versioned schema) |
| Boundaries | Max delegation depth=0 initially; scoped paths; no package install; no git push |
| Approval | Destructive/network/secret ops require human approval |
| Failure | Kill all child processes; rollback allowed files |
| Test | Property tests for task validation; mock tool execution |

## Vault

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/vault.py` |
| Algorithm | AES-256-GCM or ChaCha20-Poly1305 via Python `cryptography` |
| KDF | Argon2id or PBKDF2 with high work factor |
| Key | Derived from operator passphrase + hardware-bound token where available |
| Storage | `~/.local/share/hive/vault/` |
| Atomic writes | Yes |
| Corruption | Authenticated encryption detects tampering |
| Test | Encrypt/decrypt roundtrip; tamper detection |

## Network visibility module

| Attribute | Specification |
|-----------|---------------|
| Module | `core/lib/network.py` |
| Purpose | List listeners, routes, DNS settings; report anomalies |
| No enforcement | Cannot block traffic on standard Termux |
| Class | ADVISORY |
| Test | Mock `/proc/net` fixtures |

## Hermes adapter

| Attribute | Specification |
|-----------|---------------|
| Module | `integrations/hermes/plugin/` |
| Tools exposed | `hive_status`, `hive_doctor`, `hive_verify`, `hive_task_validate`, `hive_task_run`, `hive_agent_list`, `hive_agent_halt`, `hive_emergency_stop` |
| Invocation | Calls `hive --json ...` and parses output |
| Failure | Fails closed; returns structured error; never crashes agent loop |
| Secret access | None directly |
| Test | Plugin unit tests with mocked `hive` subprocess |
