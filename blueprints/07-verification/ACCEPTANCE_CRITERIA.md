# Acceptance Criteria

## Milestone 1 acceptance criteria

- [ ] `canonical.json` exists and is schema-valid.
- [ ] `hive` command can be invoked and shows help.
- [ ] No duplicate production entrypoints exist in runtime PATH.
- [ ] Existing user data is untouched by tests.
- [ ] CI passes lint and security scan.

## General release acceptance criteria

- [ ] All commands have documented exit codes.
- [ ] JSON output schema is stable for public commands.
- [ ] No command executes downloaded code without verification.
- [ ] Credential storage uses salted hashing.
- [ ] No plaintext or reversibly encoded password is described as secure.
- [ ] No Hive-managed service binds to non-loopback by default.
- [ ] Agent broker enforces max_delegations=0 and scoped paths.
- [ ] Hermes plugin fails closed and does not crash agent loop.
- [ ] Update has staged, verified, rollback path.
- [ ] Recovery levels 0-6 are documented and tested.
- [ ] Physical Android validation plan is executed for release.
