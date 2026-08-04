# Recovery Test Matrix

| Level | Scenario | Environment |
|-------|----------|-------------|
| 0 | Diagnose broken symlink | Physical Android |
| 1 | Repair links/permissions | Physical Android |
| 2 | Restore from staged runtime | Physical Android |
| 3 | Rollback failed update | Physical Android |
| 4 | Reinstall preserving config | Physical Android |
| 5 | Restore encrypted bundle | Physical Android |
| 6 | Destructive reset after typed confirmation | Physical Android |

Each test must verify:
- Required approvals are enforced.
- Preserved files survive.
- Rollback is possible.
