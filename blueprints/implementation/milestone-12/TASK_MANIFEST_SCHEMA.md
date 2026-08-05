# Hive Broker Task Manifest Schema

```json
{
  "schema_version": 1,
  "task_id": "user-supplied-task-id",
  "required_capabilities": ["service.status", "vault.status"],
  "intent": "inspect-service-status",
  "allowed_actions": ["service.status", "service.health"],
  "target_services": ["fixture-http"],
  "target_paths": [],
  "read_only": true,
  "timeout_seconds": 30,
  "allowed_since_commit": "dab6618",
  "audit_level": "normal"
}
```

Rules:
- `required_capabilities` must be a subset of the broker's advertised capabilities.
- `allowed_actions` must be a subset of the manifest's allowed actions and the broker's capabilities.
- Unknown fields fail closed.
- Unknown intents fail closed.
