# ADR-0006: Agent Permissions

## Status

Proposed.

## Context

The current `hive-orchestrator.py` advertises recursive, autonomous agents without bounds. This is unsafe.

## Decision

- Agent tasks use declarative, versioned manifests.
- Initial release: `max_delegations=0`.
- Tasks declare allowed read/write paths, network mode, and forbidden operations.
- Broker enforces these bounds for operations that pass through it.
- Destructive/network/secret operations require human approval.

## Consequences

- Agents cannot recursively spawn.
- Agents cannot escape declared paths.
- Same-UID bypass remains possible; documented as limitation.

## Rejected alternatives

- Recursive autonomous agents — rejected as unsafe for mobile/constrained environment.
