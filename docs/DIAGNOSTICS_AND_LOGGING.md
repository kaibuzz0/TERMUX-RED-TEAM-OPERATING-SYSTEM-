# Hive OS Diagnostics and Logging

**Version:** 1.1  
**Status:** Pass D — Unified Logging + Health / Doctor / Audit / Selftest

This document defines the Hive OS diagnostic commands and the unified logging model.

---

## Unified Logging Model

Hive OS uses one canonical logging subsystem: `runtime_logs/`.

### Goals

- One rotation engine (no competing rotators)
- Bounded service output
- Predictable log paths
- Restrictive permissions
- No secrets in logs

### Log categories

| Category | Path under log root | Purpose |
|----------|---------------------|---------|
| Service stdout | `services/<service>.log` | Captured stdout |
| Service stderr | `services/<service>.err.log` | Captured stderr |
| Runtime events | `runtime/<subsystem>.log` | Structured subsystem events |

### Rotation policy

- `max_bytes` — rotate when current log exceeds this size
- `retention_count` — number of rotated archives to keep
- `max_age_days` — optional age-based cleanup
- Compressed rotated files by default

### Permissions

- Log directories: best-effort `0700`
- Log files: best-effort `0600`
- Non-POSIX platforms degrade safely

---

## Commands

### `hive logs`

Show service logs.

```text
hive logs
hive logs SERVICE
hive logs --tail N
hive logs --follow SERVICE
hive logs --status
```

### `hive rotate-logs`

Rotate service logs.

```text
hive rotate-logs
hive rotate-logs SERVICE
hive rotate-logs --max-bytes BYTES --retention N
```

---

## `hive health`

Quick read-only health summary.

```text
hive health
hive health --json
```

Outcomes:

- `HEALTHY`
- `DEGRADED`
- `FAILED`

Exit codes:

- `0` healthy
- `1` degraded
- `2` failed

Health consumes authoritative state from:

- network manager
- service supervisor
- broker
- vault

It does not mutate state.

---

## `hive doctor`

Diagnostic findings with remediation suggestions.

```text
hive doctor
hive doctor --json
```

Doctor is read-only by default.

Findings include:

- Tor unhealthy in TOR profile
- Orbot SOCKS unreachable in ORBOT profile
- Service blocked by network
- Service crash-looping
- Dependency missing
- Vault issues

Exit codes:

- `0` no issues
- `1` warnings/errors
- `2` critical issues

Explicit repair remains `hive termux repair`.

---

## `hive audit`

Read-only security and configuration audit.

```text
hive audit
hive audit --json
```

Audit areas:

- filesystem permissions on sensitive directories
- network listener bindings (Tor must be loopback-only)
- service manifest safety
- service network requirements
- legacy-only services
- crash-looping services

Critical guarantee: **audit never mutates state.**

A regression test verifies that running `run_audit` does not change filesystem
mtimes, network profile, or service state.

Exit codes:

- `0` clean
- `1` findings
- `2` audit error

---

## `hive selftest`

Explicit active integration test with mandatory state restore.

```text
hive selftest
hive selftest --json
hive selftest --no-network
hive selftest --no-service
```

Selftest:

1. snapshots current network profile and running services
2. runs requested test steps
3. restores original state
4. reports any restoration failure

If a test fails, the original state is still restored.

Exit codes:

- `0` pass and state restored
- non-zero otherwise

---

## Severity Model

A single severity vocabulary is used across diagnostics:

- `info`
- `warning`
- `error`
- `critical`

---

## Operations Center Integration

Operations Center consumes the same diagnostic data through its existing broker-backed
collectors. Pass D does not redesign the UI; it provides the underlying model.

---

*See `docs/NETWORK_MODEL.md` for the network authority model.*
*See `docs/SERVICE_SUPERVISOR.md` for the service runtime model.*
*See `docs/ORIGINAL_RUNTIME_PARITY.md` for the OG capability mapping.*
