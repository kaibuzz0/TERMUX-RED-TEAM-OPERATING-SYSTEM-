# Legacy Installers

**Milestone 6**

## Status

- `install.sh` — **LEGACY / UNVERIFIED / NONTRANSACTIONAL / PENDING REPLACEMENT**
- `install-termux.sh` — **LEGACY / UNVERIFIED / NONTRANSACTIONAL / PENDING REPLACEMENT**

## Behavior summary

Both scripts:
- Require Termux.
- Run `pkg update` and `pkg install -y`.
- Clone or pull the repository from GitHub.
- Write files to `$HOME/hive`.
- Create symlinks in `$HOME/.local/bin` or `$HOME/bin`.
- Modify shell startup files (`.bashrc`, `.zshrc`) in `install.sh`.
- Set up Termux:Boot scripts.
- Do not produce installation manifests.
- Do not support rollback.

## Why they remain

They are retained as compatibility entrypoints until the new `installer/` package is validated on physical Android hardware and an explicit activation phase is approved.
