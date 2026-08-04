# Service Supervisor Specification

## Scope

Manage only Hive-owned services. Do not assume systemd.

## Service manifest format

```json
{
  "name": "tor-local",
  "command": ["tor", "-f", "..."],
  "working_dir": "~/.local/share/hive/services/tor-local",
  "environment": {"...": "..."},
  "bind_address": "127.0.0.1",
  "port": 9052,
  "auto_start": false,
  "restart_policy": "on-failure",
  "max_restarts": 3,
  "backoff_seconds": [1, 2, 4],
  "log_dir": "~/.local/share/hive/logs/tor-local",
  "graceful_shutdown_seconds": 5
}
```

## Requirements

- PID validation: verify PID exists and command line matches expected.
- Process-group tracking: track process groups for cleanup.
- Stale PID detection: remove PID files for dead processes.
- Startup dependencies: start services in dependency order.
- Restart policy: `no`, `always`, `on-failure`.
- Exponential backoff: prevent crash loops.
- Crash-loop cutoff: stop restarting after max failures.
- Log capture: redirect stdout/stderr to log files.
- Graceful shutdown: SIGTERM, then SIGKILL after grace period.
- Android process-death recovery: detect missing processes on next invocation.
- Optional wake-lock behavior: if Termux:API battery permission granted.
- Battery and charging policy: optional run-while-charging rules.
- Emergency stop: `hive emergency-stop` terminates all managed processes.
- Termux:Boot integration: optionally start marked services on boot.
- Foreground-only fallback: if background is unreliable, run in foreground under `hive service start --foreground`.

## Network defaults

- No service may bind to a non-loopback address by default.
- `bind_address` default is `127.0.0.1` or Unix socket.
- Remote binding requires explicit config and operator approval.
