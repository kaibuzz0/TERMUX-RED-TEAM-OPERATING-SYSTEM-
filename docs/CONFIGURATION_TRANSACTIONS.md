# Configuration Transactions

All configuration writes proceed through:

1. `load`
2. `validate`
3. `preview`
4. `stage`
5. `commit`
6. `rollback` if needed

## Atomicity

Committed configuration is written atomically via a temporary file and rename.

## History

Every commit archives a snapshot with a transaction ID and metadata.
