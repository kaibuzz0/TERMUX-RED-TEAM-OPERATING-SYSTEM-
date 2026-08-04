# Security Invariants

**Status:** target invariants for the redesigned Hive OS. Current compliance is noted.

## INV-001 — No production command executes downloaded code before verification

- **Rationale:** Prevents malicious/compromised upstream code from running automatically.
- **Enforcement component:** installer, updater, repair, plugin loader.
- **Test strategy:** verify that every remote fetch is followed by hash/signature verification before execution; test with a mismatched hash.
- **Current compliance:** PARTIAL. `install-termux.sh`, `update.sh`, `emergency-repair.sh` download from GitHub with no verification.
- **Known limitation:** Requires implementing signed/TUF update metadata.

## INV-002 — No plaintext or reversibly encoded password is accepted as secure credential storage

- **Rationale:** Base64 is encoding, not encryption. Credentials must use salted slow hashing.
- **Enforcement component:** `hive-secure-login`, credential setup.
- **Test strategy:** inspect `~/.hive_auth/passwd`; verify it contains only a salted hash, never base64 plaintext.
- **Current compliance:** VIOLATED. Current code base64-encodes password+PIN.
- **Known limitation:** README incorrectly calls this "Encryption".

## INV-003 — No agent may expand its own command, path, network, secret, or runtime permissions

- **Rationale:** Prevents runaway agents and privilege escalation.
- **Enforcement component:** agent orchestrator, toolset restrictions, allowed-path lists.
- **Test strategy:** attempt recursive delegation beyond configured depth; attempt to access paths outside allowlist.
- **Current compliance:** VIOLATED. `hive-orchestrator.py` advertises recursive agent spawning without stated bounds.
- **Known limitation:** Requires bounded task manifest design.

## INV-004 — No destructive recovery action occurs without explicit operator confirmation and a validated target path

- **Rationale:** Prevents accidental or malicious data destruction.
- **Enforcement component:** `emergency-repair.sh`, all `rm -rf` paths.
- **Test strategy:** dry-run repair; verify confirmation prompt and path validation.
- **Current compliance:** PARTIAL. Standard repair asks confirmation, but unquoted globs and possible `--full-nuke` control-flow bug remain.
- **Known limitation:** Paths are not fully quoted; destructive path not validated beyond `$HOME` prefix.

## INV-005 — No Hive-managed network service binds to a non-loopback address by default

- **Rationale:** Limits remote attack surface.
- **Enforcement component:** all tools that start HTTP/TCP services.
- **Test strategy:** start each service, inspect bound address, attempt remote connection.
- **Current compliance:** UNKNOWN. Static scan found listener patterns but runtime behavior is unverified.
- **Known limitation:** Requires runtime Android test.

## INV-006 — No update may destroy or overwrite an existing working installation before a verified rollback point exists

- **Rationale:** Keeps a known-good fallback.
- **Enforcement component:** updater with A/B or snapshot model.
- **Test strategy:** simulate failed update, verify rollback to previous working state.
- **Current compliance:** VIOLATED. `update.sh` overwrites in place; no automatic rollback image retained.
- **Known limitation:** Requires transactional update architecture.

## INV-007 — No blueprint may describe PRoot or directory workspaces as kernel-enforced isolation

- **Rationale:** Avoids false security claims.
- **Enforcement component:** documentation and architecture reviews.
- **Test strategy:** review every isolation claim; ensure it maps to a real security boundary.
- **Current compliance:** PENDING. No current blueprint makes such claims.
- **Known limitation:** Target architecture must distinguish container/PRoot workspaces from VM/hardware isolation.

## INV-008 — No component may claim Android boot security, full-device authentication, or SELinux enforcement from ordinary Termux

- **Rationale:** Termux cannot provide these guarantees.
- **Enforcement component:** README, docs, UI labels.
- **Test strategy:** review all "secure boot", "authentication", "lock" language.
- **Current compliance:** VIOLATED in README. README says "Secure Login on Boot" and "Boot-on-startup toggle"; these are Termux:Boot session prompts, not device authentication.
- **Known limitation:** Requires terminology correction.

## INV-009 — Every canonical production entrypoint must resolve through one declared control plane

- **Rationale:** Prevents conflicting commands and unclear authority.
- **Enforcement component:** canonical launcher, command registry.
- **Test strategy:** list every `hive*` command and trace it to the control plane.
- **Current compliance:** VIOLATED. Two control planes exist: `Hive Ops Final/bin/hive` and `Hive Ops DevAI/hive-ctrl.py`/`bin/hive-os`.
- **Known limitation:** Requires canonical-source decision.

## INV-010 — User work, untracked files, configuration, and secrets must survive inspection and failed upgrades

- **Rationale:** Prevents data loss during maintenance.
- **Enforcement component:** backup, update, repair.
- **Test strategy:** create user files, run failed update, verify files intact.
- **Current compliance:** PARTIAL. Backups exist but are not verified or rotated.
- **Known limitation:** Requires backup integrity checks.

## INV-011 — Security-relevant state transitions must produce bounded, secret-redacted audit events

- **Rationale:** Enables operator awareness without leaking secrets.
- **Enforcement component:** audit logger.
- **Test strategy:** trigger login, update, repair, file transfer; inspect logs for presence of passwords.
- **Current compliance:** PARTIAL. `login.log` records attempts but may include raw input.
- **Known limitation:** Requires redaction policy.

## INV-012 — Critical runtime claims require validation on a real supported Termux environment

- **Rationale:** Windows static analysis cannot prove Android behavior.
- **Enforcement component:** CI/test matrix, manual validation checklist.
- **Test strategy:** run acceptance tests on physical Android device.
- **Current compliance:** NOT MET. No physical Android validation performed.
- **Known limitation:** Phase 1 is documentation-only; validation is Phase 2+.
