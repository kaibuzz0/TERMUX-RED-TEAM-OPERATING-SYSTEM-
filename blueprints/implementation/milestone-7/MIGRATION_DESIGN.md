# Milestone 7 Legacy Migration Design

## Detection targets

- $HOME/hive
- /root/hive (via HIVE_LEGACY_ROOT or fixture override)
- unmanaged clones
- DevAI and Final trees
- shell startup modifications
- Termux:Boot scripts
- base64 credential files

## Risk classification

- SAFE: ordinary files without scripts, secrets, or shell/boot semantics
- MANUAL_REVIEW: scripts, shell startup files, Termux-specific files
- NEVER_COPY: credential-like filenames or base64 content

## Migration plan

`build_migration_plan()` returns a non-executable `MigrationPlan`.
No files are copied automatically.
Manual remediation is required for NEVER_COPY items.
