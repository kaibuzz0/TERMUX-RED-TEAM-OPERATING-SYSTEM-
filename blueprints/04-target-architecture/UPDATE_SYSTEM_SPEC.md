# Update System Specification

## Trust levels

| Level | Description | First release? |
|-------|-------------|----------------|
| DEVELOPMENT GIT UPDATE | Pull from a specific branch/commit | Internal use only |
| SIGNED RELEASE UPDATE | Signed release archive or signed git tag | Yes, target |
| OFFLINE VERIFIED BUNDLE | Pre-downloaded bundle with verified digest | Yes, target |
| EMERGENCY RECOVERY BUNDLE | Offline recovery image | Future |

## Staged update flow

```text
hive update check
    → query release metadata
    → compare local version
    → report available update

hive update stage
    → download release archive to staging dir
    → verify digest/signature
    → unpack into versioned prefix
    → run schema migration preview
    → run tests against staged files
    → preserve current runtime as rollback point

hive update apply
    → confirm with operator
    → backup state, config, vault metadata
    → atomically switch active symlink/directory
    → restart services if needed
    → run health check
    → if health check fails, automatic rollback

hive update rollback
    → restore previous runtime prefix
    → restore state/config backup
    → log rollback event
```

## Security requirements

- No automatic execution from a network pipe.
- Explicit version or commit selection.
- Expected repository remote configured.
- Cryptographic digest verification for release archives.
- Signed release metadata when signing infrastructure exists.
- Staging outside the active runtime.
- Backup before activation.
- Schema migration preview.
- Test execution against staged files.
- Atomic or recoverable activation.
- Health check after activation.
- Rollback point retained.
- Update journal maintained.
- No destruction of untracked user files.

## Rollback point

- Current runtime is preserved under `~/.local/share/hive/runtimes/<version>/`.
- Active runtime is a symlink: `~/.local/share/hive/active/`.
- Switching versions re-points the symlink.

## Do not describe raw git pull as secure

`git pull` may be used for development updates but must not be described as the secure update path. The secure path uses staged, verified release archives.
