# Configuration Rollback

Rollback restores a previous transaction snapshot without editing history. A new transaction records the rollback.

## CLI

```bash
hive config history
hive config rollback TRANSACTION_ID
```

## Restrictions

- Immutable transactions cannot be rolled back.
- Invalid transaction IDs are rejected.
