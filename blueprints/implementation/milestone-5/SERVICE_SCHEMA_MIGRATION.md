# Service Schema Migration

**Milestone 5**

## Migration stages

### Stage 1 — Schema 1 (legacy)

- `start`, `stop`, `status`, `restart` are shell command strings.
- Paths use `${HIVE_*}` tokens.
- Loaded and validated with strict safety checks.
- Deprecated but still readable.

### Stage 2 — Schema 2 (current)

- Commands are structured objects:
  ```json
  {
    "interpreter": "python|bash|sh",
    "base": "canonical-source",
    "path": "bin/hive",
    "args": ["start"]
  }
  ```
- Log paths are structured objects:
  ```json
  {
    "base": "log-root",
    "path": "supervisor.log"
  }
  ```
- No shell metacharacters.
- Argument arrays constructed explicitly.

## Future removal

Schema 1 support may be removed once all consumers have migrated and physical Termux tests confirm schema 2 behavior.
