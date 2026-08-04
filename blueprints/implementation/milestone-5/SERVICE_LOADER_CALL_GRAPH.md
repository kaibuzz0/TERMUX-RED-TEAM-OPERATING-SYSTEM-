# Service Loader Call Graph

**Milestone 5 — Identifying the actual consumer of `Hive Ops Final/etc/services.json`**

## Configuration file

`Hive Ops Final/etc/services.json`

## Direct consumers found

No Python, shell, or other source file inside `Hive Ops Final/` directly opens `services.json` by name. The only literal mention is in `Hive Ops Final/README.md` as documentation.

## Indirect consumers

The canonical launcher `Hive Ops Final/bin/hive` routes the `services` subcommand to the legacy bash script:

```text
Hive Ops Final/bin/hive:cmd_services()
  └─ self._run_bash('hive_services.sh', ...)
       └─ searches HIVE_HOME/bin/hive_services.sh
       └─ searches HIVE_OS/bin/hive_services.sh
       └─ searches /root/hive-swarm/the-hive-tools/original hive os files/bin/hive_services.sh (legacy fallback, now replaced)
```

The legacy script that actually implements service management is:

```text
Hive Ops Final/original hive os complete/bin/hive_services.sh
```

This script:

1. Sources `$HOME/.config/hive/env.sh`.
2. Looks for `.svc` files under `$HIVE_ETC/services/`.
3. Starts services by running `nohup bash -lc "$START"` or through a proxy helper.
4. Reads `START`, `LOG`, `REQUIRES_NET`, `USE_PROXY_ENV`, and `WANT_TORSOCKS` variables from each `.svc` file.

## Implication for `services.json`

`Hive Ops Final/etc/services.json` is **not currently consumed by the active service loader**. The active loader uses `.svc` files under `$HIVE_ETC/services/`. The JSON file is therefore either:

- A newer design that is not yet wired in, or
- A documentation/declaration artifact used by external tooling, or
- Intended for a future loader.

## Token-expansion classification for `services.json`

**UNSUPPORTED** — because no loader currently reads the file.

If a future loader is built, it must not rely on shell expansion to resolve `${HIVE_*}` tokens.

## Call path summary

| Command | Launcher function | Backend script | Config source |
|---------|-------------------|----------------|---------------|
| `hive services` | `cmd_services()` | `original hive os complete/bin/hive_services.sh` | `.svc` files under `$HIVE_ETC/services/` |
| `hive start` | `cmd_start()` | `original hive os complete/bin/hive_start.sh` | `$HIVE_STATE/session` |
| `hive status` | `cmd_status()` | Multiple bash probes + Python helpers | Runtime state |
| `hive health` | `cmd_health()` | `original hive os complete/bin/hive_health.sh` | Runtime state |

## Conclusion

The current service loader is in the legacy bash layer, not in the JSON file. Milestone 5 should either:

1. Build a new safe loader that consumes `services.json` with structured path expansion, or
2. Treat `services.json` as a declaration and ensure it remains valid and free of unsafe paths.

Given the directive to avoid broad rewrites, this milestone will design and validate a non-mutating structured loader for `services.json` while leaving the legacy `.svc` path untouched.
