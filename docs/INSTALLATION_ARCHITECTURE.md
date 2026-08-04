# Hive OS Installation Architecture

**Milestone 6**

## Legacy installers

- `install.sh` — Bash installer that runs `pkg install`, clones the repository, writes `$HOME/.bashrc`, and sets up Termux:Boot.
- `install-termux.sh` — Bash installer with similar behavior plus secure-login setup.

Both are **legacy, non-transactional, immediately mutating**. They are documented as such and not modified in Milestone 6.

## New installer foundation

Located under `installer/`:

- `preflight.py` — non-mutating environment detection.
- `plan.py` — deterministic plan generation.
- `staging.py` — isolated staging with manifest and journal.
- `journal.py` — append-only transaction journal.
- `verify.py` — staged manifest verification.
- `rollback.py` — rollback operation planning.
- `install.py` — CLI surface.

## Activation model (future)

1. Preflight
2. Plan generation
3. Dry-run validation
4. Staging
5. Verification
6. **Explicit user approval**
7. Atomic activation (not in Milestone 6)

## Safety rules

- Default targets stay within private Termux/user storage.
- No `/root`, `/system`, `/sdcard`, or Windows paths.
- No automatic package installation.
- No shell startup file changes.
- No network downloads during validation tests.
