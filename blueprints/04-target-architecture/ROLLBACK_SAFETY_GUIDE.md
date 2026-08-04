# Safe Blueprint Rollback Guidance

**Purpose:** describe how to remove blueprint artifacts without causing accidental data loss. This is documentation only; do not execute automatically.

## Safe rollback procedure

1. Verify repository root:
   ```bash
   cd "E:/Hermes-USB-Portable-main/TERMUX-RED-TEAM-OPERATING-SYSTEM-"
   git rev-parse --show-toplevel
   ```

2. Verify that the target is inside the repository and equals the expected blueprint directory:
   ```bash
   test -d blueprints
   realpath blueprints
   ```

3. Display the contents to confirm what will be removed:
   ```bash
   find blueprints -type f | sort | head -n 100
   ```

4. Require explicit confirmation from the operator before deletion.

5. Prefer moving to a quarantine directory before permanent deletion:
   ```bash
   mkdir -p /tmp/hive-blueprints-quarantine
   mv blueprints /tmp/hive-blueprints-quarantine/blueprints-$(date +%Y%m%d_%H%M%S)
   ```

6. Verify the move:
   ```bash
   git status --short
   ```
   Expected: no `blueprints/` directory remains.

7. Only after quarantine is verified, the operator may delete the quarantine directory.

## Forbidden rollback patterns

- Do not run `rm -rf` on a path constructed from an unverified variable.
- Do not delete files outside the repository.
- Do not delete production code (`Hive Ops Final/`, `Hive Ops DevAI/`, etc.).
- Do not delete user data (`~/.hive_auth/`, `~/.hive_backup/`, etc.).
- Do not run `git clean -fd` without first reviewing untracked files.

## Note

This guidance applies to blueprint artifacts only. Production rollback uses the recovery levels defined in the recovery model.
