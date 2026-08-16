# Hive OS v2.0.0 Acceptance Checklist

This document is the release gate for Hive OS v2.0.0. A stable v2 release must not be published while any required gate is unresolved.

## Current integration state

- Active continuation branch: `hive-1.1-rc2-bootstrap`
- Bootstrap foundation has been integrated into `master` through PR #3.
- The continuation branch is used for post-merge hardening until the full gate is green.
- Stable v2.0.0 is **not release-ready** while CI, physical Termux validation, or release-signing gates remain unresolved.

## Required gates

### Clean Termux install

- [ ] Empty-Termux bootstrap installs Hive without requiring an existing Hive runtime.
- [ ] Bootstrap uses the canonical release/trust path rather than an unverified source checkout.
- [ ] Global `hive` launcher works from outside the repository/runtime directory.
- [ ] Autoboot is idempotent and disable/reenable persists across new shells.
- [ ] Existing unrelated shell configuration is preserved.

### Update / rollback / repair

- [ ] Stable/current release can discover and verify an approved candidate.
- [ ] Update stages before activation and fails closed on verification failure.
- [ ] Previous release remains recoverable after failed activation.
- [ ] Supported rollback succeeds without violating anti-rollback policy.
- [ ] Re-applying the candidate after rollback is idempotent.
- [ ] Broken launcher/runtime/active-pointer states have a tested repair path.

### OG runtime parity

- [ ] Network profiles use the authoritative network manager.
- [ ] Service lifecycle uses the authoritative supervisor.
- [ ] Logging, health, doctor, audit, and selftest remain available.
- [ ] Hive Home reflects authoritative state and degrades safely when a subsystem fails.
- [ ] Operator notes and `hive speak` remain compatible.
- [ ] Advertised legacy commands are implemented, compatibility-mapped, replaced, deprecated, or explicitly unavailable; no ghost command is advertised.

### Security boundaries

- [ ] No unrestricted shell/exec capability is exposed through the broker.
- [ ] Mutating agent capabilities remain default-deny and policy-controlled.
- [ ] Release metadata and artifacts are authenticated through the established trust root/delegation path.
- [ ] Archive/path traversal defenses pass.
- [ ] Runtime and legacy detection tolerate unreadable host paths without escalating privileges or crashing.
- [ ] Secrets/private signing material are absent from repository artifacts and logs.

### Operator experience

- [ ] `hive`, `hive --help`, `hive version`, health/doctor/audit, network, services, logs, broker/policy, and update UX are coherent.
- [ ] Hive Home and Operations Center report consistent state.
- [ ] `[U] Updates` uses the canonical updater rather than duplicate download/install logic.
- [ ] Non-TTY / `NO_COLOR` output remains usable and JSON output remains clean.

### Release metadata / trust

- [ ] Candidate artifact is built from an immutable source commit.
- [ ] Artifact SHA-256, manifest digest, release ID, version, source revision, signing key ID, channel, and security sequence are exact and internally consistent.
- [ ] Candidate security sequence is derived from the published previous-release baseline.
- [ ] Stable channel is not silently redirected to an RC/test channel.
- [ ] GitHub prerelease/tag points to the exact candidate source revision.

### Documentation / website

- [ ] Public install instructions distinguish fresh install from update-existing-Hive.
- [ ] Website commands exactly match the shipped CLI/bootstrap behavior.
- [ ] Stable and candidate channels are clearly labeled.
- [ ] Recovery/rollback instructions are present and do not depend on developer-only Git operations.

### CI / regression

- [ ] Main CI is green on all supported Python versions.
- [ ] Security scan gate is green.
- [ ] Clean-bootstrap / candidate build workflow is green and reproducible.
- [ ] Broad regression suite has zero failures.
- [ ] `compileall` and `git diff --check` pass for release candidate source.

### Real-device validation

- [ ] Fresh install tested on a real Android/Termux aarch64 device.
- [ ] Close/reopen Termux proves autoboot of the installed release.
- [ ] Real device update to candidate succeeds through Hive's updater.
- [ ] Real device rollback succeeds and preserves user state.
- [ ] Candidate can be re-applied after rollback.
- [ ] Network/service behavior is validated without bypassing Android/Termux security boundaries.

## Current blockers / integration notes

As of the first post-merge integration pass, `master` CI is red. Confirmed failures include protected-host filesystem probing, autoboot persistence, dependency-surface mismatch, service-supervisor lifecycle behavior, and legacy compatibility tests with environment-sensitive assumptions. The continuation branch includes permission-safe runtime and legacy detection fixes; remaining CI failures must be resolved and re-run before v2 release consideration.

A stable v2 release must wait for physical Termux validation and any required release-signing step even after all automatable gates are green.
