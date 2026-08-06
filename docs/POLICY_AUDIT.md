# Policy Audit

Every decision generates a structured audit record.

## Record fields

- `decision_id`
- `request_id`
- `transaction_id`
- `actor_type`
- `actor_id` (bounded)
- `capability`
- `resource_type`
- `resource_id` (bounded)
- `decision`
- `reason_code`
- `matched_rules`
- `policy_digest`
- `configuration_profile`

Secrets are never logged.
