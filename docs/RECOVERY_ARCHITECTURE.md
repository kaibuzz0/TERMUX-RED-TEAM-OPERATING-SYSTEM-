# Hive OS Recovery Architecture

## Recovery levels

| Level | Name | Mutation | Description |
|-------|------|----------|-------------|
| 0 | Diagnose | No | Inspect metadata, pointers, manifests, locks, journal |
| 1 | Repair generated state | Yes | Stale locks, broken generated metadata, safe permissions |
| 2 | Restore current verified release | Yes | Repair active pointer, restore known-good generated files |
| 3 | Roll back previous release | Yes | Use existing rollback engine |
| 4 | Restore verified offline bundle | Yes | Preserve config/state/vault, stage, verify, activate |
| 5 | Disaster recovery | Yes | Rebuild managed runtime, restore encrypted backup |
| 6 | Destructive reset | Yes | Typed confirmation, validated target, backup offer |

## State preservation

Configuration, vault, user repositories, logs, backups, and Hermes state are never part of a release bundle and must be preserved across recovery.
