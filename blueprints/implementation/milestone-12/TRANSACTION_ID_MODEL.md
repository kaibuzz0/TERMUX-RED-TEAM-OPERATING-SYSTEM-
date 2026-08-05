# Transaction ID Model

Every broker execution receives:
- `transaction_id`: broker-generated UUID for the single execution
- `task_id`: caller-provided stable identifier
- `session_id`: broker session identifier
- `audit_id`: pointer to the audit log entry

`transaction_id` is propagated to all invoked subsystems and recorded in their logs.
