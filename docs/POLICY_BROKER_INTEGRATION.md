# Broker Integration

The Broker remains the enforcement point.

## Responsibilities

- Normalize actor
- Validate manifest
- Create policy request
- Call evaluator
- Enforce decision
- Obtain confirmation when required
- Dispatch only after authorization
- Record audit

The Broker may not override `DENY` or reinterpret `CONFIRM` as `ALLOW`.
