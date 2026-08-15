# Hive OS Service Supervisor

**Version:** 1.1  
**Status:** Pass C — Modern Service Supervisor + Fail-Closed Network Coupling

This document defines the canonical Hive OS service lifecycle, network coupling, and security boundaries.

---

## Service Manifest

A service is defined by a JSON manifest with `schema_version: 1`.

### Core fields

| Field | Purpose |
|-------|---------|
| `name` | Unique service identifier |
| `enabled` | Whether the supervisor should consider the service |
| `command.interpreter` | `python`, `bash`, `sh`, `direct-executable` |
| `command.path` | Relative path to executable |
| `command.args` | Argument vector |
| `working_directory` | Base/relative working directory |
| `environment.allow` | Allowed inherited environment variables |
| `environment.set` | Explicit environment variable additions |
| `network.required` | Boolean: service needs Hive network to run |
| `network.profile` | `direct`, `orbot`, `tor`, `proxied`, `any` |
| `network.use_proxy_env` | Inject Hive proxy environment at startup |
| `health_check.type` | `process`, `command`, `tcp-local`, `http-local`, `file`, `none` |
| `restart.policy` | `never`, `on-failure`, `always`, `unless-stopped` |
| `dependencies` | List of Hive services that must run first |
| `logging.stdout` / `logging.stderr` | Relative log paths |
| `shutdown.signal` / `shutdown.timeout_seconds` | Clean shutdown behavior |

### Manifest security

- Command args are validated as strings.
- Shell metacharacters are rejected.
- Path traversal is rejected.
- Non-loopback health-check hosts are rejected.
- Logging paths must be relative under the log root.

---

## Service Lifecycle States

- **DEFINED** — Manifest loaded
- **STOPPED** — Not running
- **STARTING** — Start initiated
- **RUNNING** — Process alive and healthy
- **DEGRADED** — Running but health check failing
- **STOPPING** — Shutdown in progress
- **FAILED** — Failed startup/health
- **CRASH_LOOP** — Exceeded restart policy window
- **BLOCKED_NETWORK** — Ineligible due to network requirement
- **BLOCKED_DEPENDENCY** — Ineligible due to missing dependency

---

## Network Coupling

The network subsystem (`network/`) is the single authority for network state.

### Fail-closed behavior

| Network profile | Effect on network-required services |
|-----------------|-------------------------------------|
| `DIRECT` | Services requiring `tor`/`orbot`/`proxied` are blocked |
| `TOR` | Services requiring `orbot` are blocked; `proxied` allowed |
| `ORBOT` | Services requiring `tor` are blocked; `proxied` allowed |
| `HOLD` | All network-required services are blocked |

When the network profile changes and a running service becomes ineligible, the supervisor **stops** that service and records the state as `BLOCKED_NETWORK`.

Recovery is policy-controlled: when the network condition returns, the service is restarted only according to its `restart` policy, not blindly.

### No silent fallback

A service requiring `tor` is **never** silently allowed to run under `DIRECT` just because Tor is unavailable.

---

## Process Ownership

The supervisor tracks exact child processes:

- PID
- Start time
- Command digest
- Manifest digest
- Session ID
- Restart count

Signals are sent only after identity validation.

`pgrep -f` / `pkill -f` are **not** used.

---

## Restart Policy

- `never` — Do not restart
- `on-failure` — Restart on non-zero exit
- `always` — Always restart unless manually stopped
- `unless-stopped` — Restart unless manually stopped

### Crash-loop protection

If `max_attempts` is exceeded within `window_seconds`, the service enters `CRASH_LOOP` state and requires operator intervention.

Backoff grows exponentially from `backoff_initial_seconds` up to `backoff_max_seconds`.

---

## Dependencies

Services declare dependencies as a list of service names. The supervisor:

- Validates the dependency graph
- Detects cycles and rejects them
- Starts services in topological order
- Stops services in reverse dependency order
- Records `BLOCKED_DEPENDENCY` if a dependency is not running

---

## Clean Shutdown

1. Send configured signal (`TERM` by default)
2. Wait up to `timeout_seconds`
3. If still running and `kill_after_timeout` is true, send `SIGKILL`
4. Record exit code and final state

Identity is re-validated before every signal.

---

## Legacy `.svc` Compatibility

Original Hive OS `.svc` files are parsed textually, **never sourced or executed**.

Recognized fields:

- `START`
- `PROBE`
- `REQUIRES_NET`
- `USE_PROXY_ENV`
- `WANT_TORSOCKS`
- `LOG`

Rejected constructs:

- Command substitution
- Pipelines
- Redirections
- Dynamic sourcing
- `pkill` / `killall`
- `curl` / `wget`
- Privilege escalation

The parser produces a migration plan, not an executable service.

---

## Security Boundaries

- No arbitrary legacy shell execution
- Exact process ownership
- Network state is authoritative and not duplicated
- Restrictive permissions on state files
- No secrets in service logs
- No shell reconstruction in health checks or proxy runner
- Fail-closed network coupling

---

## Commands

| Command | Purpose |
|---------|---------|
| `hive start` | Start all eligible services |
| `hive stop [NAME]` | Stop service(s) |
| `hive restart [NAME]` | Restart service(s) |
| `hive status [NAME]` | Show status |
| `hive services list` | List services |
| `hive services status [NAME]` | Alias for status |
| `hive services health [NAME]` | Show health |
| `hive services start NAME` | Start one service |
| `hive services stop NAME` | Stop one service |
| `hive services restart NAME` | Restart one service |
| `hive services ensure` | Ensure eligible services are running |
| `hive services ps` | List Hive-owned processes |
| `hive services validate` | Validate all manifests |
| `hive services graph` | Show dependency order |

---

*See `docs/NETWORK_MODEL.md` for the network authority model.*
*See `docs/ORIGINAL_RUNTIME_PARITY.md` for the OG-to-modern mapping.*
