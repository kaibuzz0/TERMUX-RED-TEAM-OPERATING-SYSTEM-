# Network Exposure Audit

## Static findings

The security-risk-register scan found network-listener and remote-service patterns in multiple files. The following is a list of files that contain such strings, not proof that the services bind to remote interfaces.

| File | Pattern observed | Potential risk |
|------|------------------|----------------|
| `brain-plug/therapist_code only.py` | `Flask`, `jsonify`, `/api` endpoints | Could start a web service; binding address unknown without runtime check |
| Various `Hive Ops DevAI/bin/hivedev-*` | `0.0.0.0`, `listen`, `bind`, `http.server`, `webhook`, `dashboard` | Some tools may bind network listeners |
| `Hive Ops DevAI/bin/hivedev-gateway` | likely gateway server | UNVERIFIED |
| `Hive Ops DevAI/hive-gateway.py` | gateway module | UNVERIFIED |
| `Hive Ops DevAI/bin/hivedev-comms` / `hivedev-comms3` | communications tools | UNVERIFIED |

## Default binding policy

No repository-wide policy was found that defaults services to `127.0.0.1` or Unix sockets. The target architecture must add invariant INV-005.

## Public exposure scenarios

- If any tool starts `http.server` with default `0.0.0.0` or `8000`, the device may be reachable on local Wi-Fi.
- If Flask defaults to `127.0.0.1`, the risk is lower but still present if combined with port forwarding or ADB.

## Required remediation

1. Audit every file containing `listen`, `bind`, `server`, `app.run`, `http.server`.
2. Default all services to `127.0.0.1` or Unix sockets.
3. Require explicit `--bind 0.0.0.0` or config flag for remote exposure.
4. Add a `hive network listeners` command to list bound ports.
