# Legacy to Native Mapping

## Goals

- Preserve the known-working Android/Termux runtime as a compatibility fallback.
- Do not delete legacy `.svc` files.
- Do not auto-start legacy services in native mode.
- Provide a non-mutating migration plan.

## Mapping table

| Legacy concept | Native concept | Notes |
|---|---|---|
| `.svc` filename | native manifest `name` | stripped `.svc` extension |
| `START` string | `command.args` array | Must be parsed into safe argument array; shell metacharacters rejected |
| `PROBE` string | `health_check` block | Map `nc -z HOST PORT` to `tcp-local` health check with loopback validation |
| `REQUIRES_NET` | `environment.allow` / policy | May become explicit dependency or network policy |
| `USE_PROXY_ENV` / `WANT_TORSOCKS` | `environment.set` / proxy policy | Explicit, opt-in, no secret leakage |
| `LOG` | `logging.stdout` / `logging.stderr` | Must be under LOG_ROOT |
| implicit list | `registry` loading manifests | Deterministic order, duplicate detection |
| `pgrep -f` PID | `process` tracking | Start time, command digest, manifest digest, process group |
| `pkill -f` stop | `shutdown` sequence | Graceful signal, timeout, process-group escalation |
| no dependency info | `dependencies` array | Topological ordering |
| no restart policy | `restart.policy` | Default `never`; optional `on-failure` / `always` / `unless-stopped` |
| `ensure` auto-start | not implemented | Native supervisor never auto-starts services by default |

## Service classifications

| Service | Proposed classification |
|---|---|
| `_TEMPLATE` | DISABLED (underscore prefix; example only) |
| `mini-ai` | LEGACY_ONLY until reviewed and converted to argument-array command |
