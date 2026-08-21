# Hive OS Safe Installer Foundation

**Milestone 6**

This package provides a transactional, staged, auditable installation foundation for Hive OS. It does **not** replace the legacy `install.sh` / `install-termux.sh` entrypoints yet.

## Commands

- `python3 -m installer.install check` — run non-mutating preflight checks.
- `python3 -m installer.install plan [--json]` — generate a deterministic installation plan.
- `python3 -m installer.install dry-run` — validate the plan without mutating the system.
- `python3 -m installer.install stage TARGET` — verify a staged installation directory.
- `python3 -m installer.install verify TARGET` — alias for `--stage`.

## Design principles

- No command requires root.
- No command installs packages.
- No command modifies `.bashrc`, `.zshrc`, or Termux:Boot scripts.
- No command starts services or opens listeners.
- All mutation happens inside a validated staging area first.
- Every operation is recorded in an append-only journal.
- Source files are manifest-hashed before staging.

## Activation

Real activation of a staged installation is intentionally not implemented in Milestone 6. It is deferred until physical Termux validation proves the staging model is safe.
