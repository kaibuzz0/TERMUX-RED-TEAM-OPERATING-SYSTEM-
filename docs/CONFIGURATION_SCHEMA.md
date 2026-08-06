# Configuration Schema

Every subsystem has a typed schema registered in `config_engine.defaults`.

## Subsystems

- `runtime`
- `broker`
- `services`
- `vault`
- `updates`
- `recovery`
- `operations_center`
- `plugins`

## Field types

Schemas declare field type, required/optional status, ranges, enumerations, deprecation, and nested schemas.

## Unknown fields

By default unknown fields cause validation errors. Subsystems may opt into extensibility.
