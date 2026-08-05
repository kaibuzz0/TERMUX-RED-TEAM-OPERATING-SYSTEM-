# Legacy Service Call Graph

## Source location

`Hive Ops Final/original hive os complete/bin/hive_services.sh`

## Entry points

- `list` — enumerate `*.svc` in `$HIVE_ETC/services`, excluding `_*`.
- `describe SERVICE` — cat the `.svc` file.
- `start SERVICE...` — source `.svc`, then `start_one`.
- `stop SERVICE...` — source `.svc`, then `stop_one`.
- `status [SERVICE...]` — defaults to all services; source `.svc`, then `status_one`.
- `health` — checks active SOCKS proxy, then probes each service.
- `ensure` — starts every listed service (no-op if running).

## `start_one` call graph

1. Source `$SERV_DIR/$name.svc` (executes arbitrary shell in caller context).
2. Default variables: `LOG`, `REQUIRES_NET=1`, `USE_PROXY_ENV=0`, `WANT_TORSOCKS=0`.
3. Read network mode from `$MODE_FILE` or `$HIVE_PROXY_MODE`.
4. If `mode=off` and `REQUIRES_NET=1`, return 2.
5. If `REQUIRES_NET=1` and SOCKS not reachable, return 3.
6. `pid_of "$START"` via `pgrep -f -u $(id -u) -- "$START"`.
7. If running, return 0.
8. If `USE_PROXY_ENV=1` or `WANT_TORSOCKS=1`, run `nohup "$HIVE_BIN/hive_proxy_run.sh" -- "$START" >>"$LOG" 2>&1 &`.
9. Else run `nohup bash -lc "$START" >>"$LOG" 2>&1 &`.
10. Sleep 1.
11. Re-probe with `pgrep -f`.

## `stop_one` call graph

1. Source `.svc`.
2. `pid_of "$START"` via `pgrep -f`.
3. `pkill -f -- "$START"`.
4. Poll up to 5 seconds.
5. If still running, `pkill -9 -f -- "$START"`.

## `status_one` call graph

1. Source `.svc`.
2. `pid_of "$START"` via `pgrep -f`.
3. Log running or stopped.

## `probe_one` call graph

1. Source `.svc`.
2. If `PROBE` defined, run `bash -lc "$PROBE"`.

## External dependencies

- `$HOME/.config/hive/env.sh`
- `$HIVE_STATE/net.mode`
- `$HIVE_ETC/services`
- `$HIVE_LOG`
- `$HIVE_BIN/hive_proxy_run.sh`
- `pgrep`, `pkill`, `nc`, `nohup`, `bash`, `id`, `cat`, `printf`
