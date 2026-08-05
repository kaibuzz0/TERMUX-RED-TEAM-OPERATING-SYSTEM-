# Hive OS Update Architecture

**Milestone 10**

## Trust levels

- `DEVELOPMENT_GIT`: development-only, never a secure update.
- `SIGNED_RELEASE`: versioned archive with manifest, digest, and signature.
- `OFFLINE_VERIFIED_BUNDLE`: all artifacts included, no network required, verified before staging.
- `EMERGENCY_RECOVERY_BUNDLE`: minimal recovery surface, explicit operator confirmation.

## Metadata

`metadata.json` carries:

- `schema_version`
- `release` block (version, release_id, commit, platforms, architectures, security_sequence)
- `artifacts` list (name, size, sha256)
- `manifest_digest`
- `signing` block (algorithm, key_id, signature)
- `revocation` sequence

## Signing

- Ed25519 via `cryptography`.
- Public trust store file in PEM format.
- Private signing keys never enter the repository or runtime.

## Update lifecycle

1. `hive update verify BUNDLE` — offline verification.
2. `hive update plan BUNDLE` — non-mutating plan.
3. `hive update stage BUNDLE` — stage through installer engine.
4. `hive update apply BUNDLE` — activate through Milestone 7 engine (future).
5. `hive update rollback` — rollback to prior release.

## Restrictions

- No raw `git pull` as a secure update.
- No in-place overwrite of active runtime.
- No automatic apply.
- No network by default.
