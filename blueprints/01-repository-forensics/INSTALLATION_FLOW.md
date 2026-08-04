# Installation Flow

## Source Script: `install-termux.sh`

**Entry line:** `#!/data/data/com.termux/files/usr/bin/bash`
**Options:** none (interactive) or `curl ... | bash` (non-interactive)
**Target install directory:** `$HOME/Hive-Ops`
**Log:** `$HOME/hive_install.log`

### Step-by-step flow

1. `set -euo pipefail`, `umask 077`.
2. `check_termux()`
   - Requires `$TERMUX_VERSION` or `/data/data/com.termux` directory.
   - Requires `pkg` command.
3. `install_deps()`
   - `pkg update -y`
   - Installs: `git python python-pip curl wget nano vim tmux openssh openssl-tool termux-api tor torsocks net-tools procps psmisc lsof jq clang make cmake ncurses-utils`
   - Installs each with `pkg install -y`, warns on failure.
4. `get_repo()`
   - If `$HOME/Hive-Ops/.git` exists, `cd` and `git pull --depth 1`.
   - Else `rm -rf "$INSTALL_DIR"` and `git clone --depth 1`.
5. `install_components()`
   - `mkdir -p "$HOME/bin"`.
   - For each file in `"$INSTALL_DIR/Hive Ops Final/bin"/hive*`, `ln -sf` into `$HOME/bin/$name`.
   - Appends `export PATH="$HOME/bin:$PATH"` to `~/.bashrc` if missing.
   - Sources `Hive Ops Final/etc/bash-integration.sh` in `~/.bashrc` if `hive_ops_banner` not already present.
6. `setup_secure_login()`
   - Copies `Hive Ops Final/.termux/boot/00-hive-secure.sh` to `~/.termux/boot/00-hive-secure.sh`.
   - `chmod +x` the boot script.
7. `setup_credentials()`
   - If `~/.hive_auth/passwd` does not exist, prompts password (min 4 chars) and 4-digit PIN, concatenates them with newline, encodes with `base64`, writes to `~/.hive_auth/passwd`, `chmod 600`.
8. `finish()` — prints completion banner.

## Source Script: `install.sh`

**Entry line:** `#!/bin/bash`
**Target install directory:** `$HOME/hive`

### Step-by-step flow

1. `set -e`.
2. `check_termux()` — same as above.
3. `install_deps()` — updates packages, installs the same large package list, upgrades pip.
4. `clone_repo()` — if `~/hive` exists, `git pull`; else clone.
5. `setup_directories()` — creates `~/hive/{bin,lib,logs,state,etc,backups,shared}`, `~/.local/bin`, `~/.termux/boot`, `~/.config/hive`.
6. `install_components()` — from `Hive Ops DevAI/bin/hive*` and `hivedev*`, chmod +x and symlink to `~/.local/bin` and `~/hive/bin`.
7. `setup_environment()` — writes `~/.config/hive/env.sh` with HIVE_HOME, PATH, and HERMES_HIVE_MODE/BRIDGE env vars.
8. `setup_bashrc()` — appends source line for env.sh and PATH updates to `~/.bashrc`.
9. `setup_termux_boot()` — copies `Hive Ops DevAI/bin/hive-boot` to `~/.termux/boot/00-hive-devai`.
10. `perform_first_boot()` — runs `hive-ctrl health`.

## Cross-script observations

- `install-termux.sh` links `Hive Ops Final/bin/hive*` into `~/bin`.
- `install.sh` links `Hive Ops DevAI/bin/hive*` and `hivedev*` into `~/.local/bin`.
- Both modify `~/.bashrc` and `~/.termux/boot`.
- Neither verifies package checksums or signed archives.
- Neither is transactional: partial failures leave a half-modified `~/.bashrc` and partial symlinks.
- Neither records a manifest of files it modifies.
- The same device could end up with overlapping symlinks from both installers if both are run.
