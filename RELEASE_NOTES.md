# Hive OS FINAL PRODUCTION Release Notes

## Remediation branch: hive-v2-remediation

### Status

All dependency-ready remediation items from Issue #7 are completed.
Full test suite: **1487 passed, 27 skipped** (3 non-fatal Windows concurrency warnings).

### Key changes

- Canonical runtime: `bin/hive` is the single authoritative dispatcher; historical duplicate launchers moved to `blueprints/deprecated/`.
- Trust anchor consolidated: canonical public PEM at `updates/trust_store/hive-release.pem`; signed 1.0.0 release bundle preserved under `evidence/historical-releases/`.
- Service process identity/lifecycle: `Supervisor` spawns via `TrackedProcess.start` with OS-derived start time.
- Proxy/environment isolation: `NetworkManager.proxy_env` builds on manifest-filtered environment.
- Tor ownership/confirmation: persisted identity with stale-PID rejection; confirmation parses `IsTor=true`.
- Windows ACL transactional rollback: snapshot and restore SECURITY_DESCRIPTOR.
- Restart zero-window crash-loop regression tests added.
- CI: Actions pinned to SHA, lint gates scoped, dependabot enabled, Termux smoke simulation job added.
- Documentation hygiene lint: no new absolute host-specific paths in production docs.

### Remaining hard gates

- Physical Android/Termux operator validation.
- Production signing ceremony and signed artifact publication.
- Final release tag/version identity approved by operator.
