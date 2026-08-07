# Failure Containment

Plugin failures must not crash Hive.

## Handled Failures

- malformed manifest
- incompatible SDK
- missing capability
- policy denial
- timeout
- nonzero exit
- invalid/excessive output
- corrupt config
- missing dependency
- exception
- repeated failure

## Responses

- first failure → DEGRADED
- repeated failure → QUARANTINED
- no infinite auto-restart
