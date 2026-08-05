# Legacy Service Manifest Ledger

| Service | File | START | PROBE | REQUIRES_NET | USE_PROXY_ENV | WANT_TORSOCKS | LOG | Status |
|---|---|---|---|---|---|---|---|---|
| _TEMPLATE | `etc/services/_TEMPLATE.svc` | `python -m http.server 8000` | `nc -z 127.0.0.1 8000` | 1 | 1 | 0 | default | EXCLUDED (underscore prefix) |
| mini-ai | `etc/services/mini-ai.svc` | `python -m http.server 11434` | `nc -z 127.0.0.1 11434` | 1 | 1 | 0 | default | LEGACY_ONLY |

## Notes

- Both `.svc` files use command strings executed via `bash -lc`.
- Both `START` values run the stdlib HTTP server on loopback ports.
- Both require network mode not `off` and active SOCKS.
- No dependency declarations exist in legacy format.
- No restart policy, no process-group handling, no structured health check.
- PID tracking relies solely on `pgrep -f` against the start command string.
