# Agent Control Specification

## Overview

The agent broker executes declarative, versioned task manifests. It is **broker-enforced** for tasks that run through it, but it cannot prevent an operator or same-UID process from bypassing it.

## Task manifest schema

```yaml
schema_version: 1

task:
  id: "HIVE-EXAMPLE-001"
  role: builder
  objective: "Implement one approved component."
  max_turns: 20
  max_runtime_minutes: 30
  max_changed_files: 10
  max_processes: 4
  max_delegations: 0

repository:
  root: "."
  expected_remote: "https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-"
  expected_branch: "master"
  expected_head: "..."

permissions:
  read_paths:
    - "core/"
    - "tests/"
  write_paths:
    - "core/component/"
    - "tests/component/"
  forbidden_paths:
    - ".git/"
    - "vault/"
    - "~/.hermes/"
  network:
    mode: deny
  package_installation: false
  git_commit: false
  git_push: false
  destructive_operations: false
  secrets:
    allowed:
      - "development-signing"

verification:
  commands:
    - "python -m pytest tests/component/"
  required_artifacts:
    - "core/component/__init__.py"
  rollback:
    - "git checkout -- core/component/ tests/component/"

audit:
  redact_secrets: true
  log_level: info
```

## Validation rules

- Schema version must be recognized.
- Task ID must be unique and match a safe format.
- Repository identity must match expected remote/branch/head.
- All paths must be normalized and contained within the repository root.
- No symlink traversal outside allowed paths.
- No forbidden path may be read or written.
- Network mode must be `deny`, `mirror`, or `allowlist`.
- `max_delegations` must be 0 in initial release.
- Package installation must be false by default.
- Git commit/push must be false by default.
- Destructive operations must require explicit `true` and broker approval.

## Execution rules

- Spawn child process with workspace environment.
- Apply `max_processes` limit.
- Capture stdout/stderr to workspace log.
- Enforce runtime timeout.
- Terminate all descendants on timeout or failure.
- Record every tool call in audit log.
- Diff changed files; reject if diff exceeds `max_changed_files`.

## Failure behavior

- Schema invalid → reject before execution.
- Path violation → terminate immediately, log security event.
- Network violation → terminate immediately.
- Tool failure → follow task-defined fallback or stop.
- Same-tool repeated failure → halt task and alert operator.
- Timeout → terminate process tree.

## Delegation limits

Initial release: `max_delegations: 0`. Agent tasks cannot spawn sub-agents. Future versions may allow bounded delegation only after explicit operator opt-in and additional controls.

## Secret handling

- Agents do not receive raw secrets.
- They request a capability from the vault broker.
- Broker returns signature or scoped token, not the underlying key.
- Agent logs are redacted before audit capture.

## Bypass acknowledgment

The broker cannot stop an operator or malicious same-UID process from running commands outside Hive. It can only enforce policy on operations that pass through it.
