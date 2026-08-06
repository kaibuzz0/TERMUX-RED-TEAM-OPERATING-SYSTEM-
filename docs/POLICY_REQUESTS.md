# Policy Requests

Policy requests are strict, versioned, and fail closed.

## Schema version

Only schema version `1` is supported in Milestone 15.

## Required fields

- `schema_version`
- `request_id`
- `actor` (type, id)
- `capability`
- `resource` (type, id)
- `context`

## Validation

- Unknown schema versions fail.
- Unknown actor, capability, or resource types fail.
- Oversized or malformed requests fail.
- Duplicate JSON keys are rejected.
