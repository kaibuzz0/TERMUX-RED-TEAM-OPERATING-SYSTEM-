# Service Manifests

Service manifests are versioned JSON files under `etc/services.d/`.

## Schema highlights

- `name`: validated service identifier.
- `enabled`: must be `true` to start; default false.
- `command.interpreter`: `python`, `bash`, `sh`, or `direct-executable`.
- `command.args`: argument array; shell metacharacters rejected.
- `dependencies`: ordered list of service names.
- `health_check.type`: `process`, `command`, `tcp-local`, `file`, or `none`.
- `restart.policy`: `never`, `on-failure`, `always`, `unless-stopped`.
- `shutdown`: graceful signal, timeout, optional escalation.

## Path bases

Manifests must use approved path bases from `lib/hive_path.py`.
