# Legacy Service Risk Ledger

## High-risk patterns

| Pattern | Location | Risk | Migration class |
|---|---|---|---|
| `bash -lc "$START"` | `hive_services.sh:68` | Arbitrary command string execution | UNSUPPORTED_SHELL |
| `bash -lc "$PROBE"` | `hive_services.sh:124` | Arbitrary command string execution | UNSUPPORTED_SHELL |
| `. "$file"` sourcing | `hive_services.sh:44,84,109,122` | Executes file in caller shell context | UNSUPPORTED_SHELL |
| `pgrep -f` / `pkill -f` | `hive_services.sh:38,89,99` | Broad process matching by command line | DANGEROUS |
| `nohup` backgrounding | `hive_services.sh:66,68` | Unmanaged daemonization | REQUIRES_REVIEW |
| Implicit PATH lookup | `python`, `nc`, `bash` | May resolve wrong binary | REQUIRES_REVIEW |
| `$HIVE_BIN/hive_proxy_run.sh` invocation | `hive_services.sh:66` | External helper with proxy environment | REQUIRES_REVIEW |
| Network dependency on SOCKS mode | `hive_services.sh:52-57` | Hard-codes proxy assumptions | REQUIRES_REVIEW |
| No dependency ordering | all | Services start independently | REQUIRES_REVIEW |
| No restart/backoff policy | all | Crash loops possible | REQUIRES_REVIEW |
| `ensure` auto-starts all | `hive_services.sh:149-152` | Automatic service startup | DANGEROUS |

## Safe-to-translate fields

| Field | Notes |
|---|---|
| service name from filename | SAFE_TO_TRANSLATE |
| `START` intent | REQUIRES_REVIEW (must become argument array) |
| `PROBE` intent | REQUIRES_REVIEW (must become typed health check) |
| `REQUIRES_NET` | REQUIRES_REVIEW (may become dependency/policy) |
| `USE_PROXY_ENV` | REQUIRES_REVIEW (environment policy) |
| `WANT_TORSOCKS` | REQUIRES_REVIEW (environment policy) |
| `LOG` path | REQUIRES_REVIEW (must be under LOG_ROOT) |

## Unacceptable for direct translation

- Sourcing `.svc` files.
- `bash -lc` command strings.
- `pgrep -f` / `pkill -f` as primary process identity.
- Auto-start all services (`ensure`).
- Unbounded `nohup` backgrounding.
