# Hive OS Service Supervisor

Milestone 11 introduces a native, structured, testable service supervisor that coexists with the legacy `.svc` Bash lifecycle.

## Design goals

- Replace unsafe shell-based service execution with argument-array process creation.
- Provide dependency ordering, health checks, restart policies, and crash-loop protection.
- Preserve the legacy `.svc` system as a compatibility fallback.
- Never auto-start services by default.

## Commands

- `hive service list`
- `hive service show SERVICE`
- `hive service validate`
- `hive service graph`
- `hive service start SERVICE`
- `hive service stop SERVICE`
- `hive service restart SERVICE`
- `hive service status SERVICE`
- `hive service health SERVICE`
- `hive service logs SERVICE`
- `hive service reset SERVICE`
- `hive service migrate-legacy`
- `hive service legacy-status`
