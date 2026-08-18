# AI Agent Operating Contract — {{PROJECT_NAME}}

Read `README.md`, `ops/CURRENT_STATE.md`, `docs/PROJECT_BLUEPRINT.md`, `docs/WORK_QUEUE.md`, the latest `docs/AGENT_HANDOFF.md`, recent commits, open PRs/issues, and CI before changing code.

Rules:
- Work on one bounded objective at a time.
- Preserve sources, timestamps, hashes, fixtures, assumptions, and provenance when relevant.
- Never turn assumptions into verified claims.
- Add deterministic tests when behavior changes.
- Test documented direct commands exactly as documented.
- Do not commit secrets, credentials, private keys, personal data, or generated junk.
- Do not silently overwrite another agent's active work.
- Extend canonical registries/workflows instead of inventing duplicates.
- New tools/components remain incomplete until location, command/API, inputs, outputs, dependencies, tests, docs, maturity, owner, and related work are recorded in `data/integration_queue.json` or the project's canonical registry.

Every pass must orient, verify baseline, execute one bounded change, validate it, then append a handoff with exact verification, risks, and next action. Update `ops/CURRENT_STATE.md` when repository truth materially changes.
