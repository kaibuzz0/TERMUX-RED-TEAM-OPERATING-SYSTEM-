# Compatibility Plan

## Compatibility layer

- `core/lib/compat.py` maps old command names to canonical commands.
- Old symlinks (`hive-ui-v2`, `hive-secure-login`) remain during deprecation.
- Deprecated commands emit warnings pointing to new commands.

## Deprecation timeline

- Phase 1 (M1-M6): old and new commands coexist.
- Phase 2 (M7-M10): old commands emit warnings.
- Phase 3 (M11+): old commands removed or moved to archive.

## Configuration compatibility

- Old `~/.config/hive/env.sh` keys migrated to new schema with warnings.
- Old `~/.hive_auth/passwd` base64 file migrated to hashed vault on first unlock.
