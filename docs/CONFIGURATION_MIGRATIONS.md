# Configuration Migrations

The migration engine evolves subsystem schemas while preserving data.

## Supported operations

- Rename fields
- Remove fields
- Split/merge fields
- Insert defaults

## Rules

- Migrations are registered per subsystem.
- Downgrades are rejected.
- Migrations that do not update `schema_version` fail.
- Data is never silently lost.
