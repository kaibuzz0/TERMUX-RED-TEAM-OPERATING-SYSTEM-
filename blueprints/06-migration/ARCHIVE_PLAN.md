# Archive Plan

## Items to archive

| Path | Destination | Timing |
|------|-------------|--------|
| `Hive Ops DevAI/` | `archive/devai-legacy/` | After M10 (Hermes plugin) |
| `Hive Ops Final/original hive os complete/` | `archive/original-hive-os-complete/` | After M2 (compatibility launcher) |
| `install.sh` | `archive/legacy-installers/` | After M5 (safe installer) |
| `brain-plug/` | `integrations/brain-plug/` or `archive/brain-plug/` | After port decision |

## Archive rules

- Archived code must not be in runtime PATH.
- Runtime imports from archive are forbidden.
- Tests must fail if code imports from archive paths.
- Git history is preserved.
