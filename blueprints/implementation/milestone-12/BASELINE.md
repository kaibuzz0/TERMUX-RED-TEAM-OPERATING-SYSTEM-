# HIVE OS MILESTONE 12 BASELINE

**Status: PLANNING ONLY — no code changes yet**

## Release gate

Milestone 11 fully released and accepted:
- Commit: `dab6618`
- Branch: `master`
- CI: all six checks passed (test 3.9, 3.10, 3.11, 3.12, security, build)
- Local tests: 285 passed
- Supervisor tests: 34 passed
- Working tree: clean

## Starting HEAD

`dab6618 Milestone 11: add native service supervisor`

## Scope

Milestone 12 integrates Hive OS with Hermes Agent through a **bounded, non-privileged broker** rather than by modifying Hermes core or hardwiring unsafe capabilities.

## Constraints

- No modification to Hermes Agent core, skills, or prompts.
- No unrestricted shell tool.
- No automatic activation of Hive services.
- No broad `sys.path` mutation.
- No DevAI keyword-to-weapon routing.
- No credential exposure to the broker.
- All actions mediated by explicit task manifest.
- Emergency stop must be reachable from both sides.
