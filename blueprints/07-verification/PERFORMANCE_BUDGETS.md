# Performance Budgets

| Operation | Target budget | Measurement environment |
|-----------|---------------|---------------------------|
| `hive status` warm | < 500 ms | Physical Android, warm cache |
| `hive status` cold | < 1.5 s | Physical Android, after process restart |
| `hive doctor` (no network) | < 5 s | Physical Android |
| Idle supervisor RSS | < 50 MB | Physical Android |
| Persistent default services | zero | N/A |
| Default background agents | zero | N/A |
| Workspace creation (no PRoot) | < 3 s | Physical Android |
| Workspace creation (existing PRoot image) | < 15 s | Physical Android |
| Emergency stop begin | < 1 s | Physical Android |
| Emergency stop complete (cooperative) | < 10 s | Physical Android |
| Log storage | bounded by retention | Physical Android |

## Note

These are target budgets requiring measurement. They are not guarantees until validated.
