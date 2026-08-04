# Legacy Installer Call Graph

**Milestone 6 — Static audit of `install.sh` and `install-termux.sh`**

## Files analyzed

- `install.sh` (439 lines, Bash)
- `install-termux.sh` (223 lines, Bash)

No installer was executed during this audit.

## `install.sh` call graph

```text
main()
  ├─ check_termux()
  │    └─ exits if $TERMUX_VERSION empty and /data/data/com.termux missing
  │    └─ exits if pkg not available
  ├─ install_deps()
  │    ├─ pkg update -y
  │    ├─ pkg install -y <43 packages>
  │    └─ pip install --upgrade pip setuptools wheel
  ├─ clone_repo()
  │    ├─ git pull origin master (if $INSTALL_DIR exists)
  │    └─ git clone --depth 1 $REPO_URL $INSTALL_DIR
  ├─ setup_directories()
  │    ├─ mkdir -p $INSTALL_DIR/{bin,lib,logs,state,etc,backups,shared}
  │    ├─ mkdir -p $HOME/.local/bin
  │    ├─ mkdir -p $HOME/.termux/boot
  │    └─ mkdir -p $HOME/.config/hive
  ├─ install_components()
  │    ├─ find "Hive Ops DevAI/bin" -type f
  │    ├─ chmod +x each
  │    ├─ ln -sf into $HOME/.local/bin
  │    └─ ln -sf into $BIN_DIR
  ├─ setup_environment()
  │    ├─ export HIVE_HOME, HIVE_BIN, HIVE_LOG, HIVE_STATE, HIVE_ETC, HIVE_SHARED
  │    └─ appends exports to $HOME/.bashrc and $HOME/.zshrc
  ├─ create_cli()
  │    ├─ writes $HOME/.local/bin/hive launcher script
  │    └─ chmod +x
  ├─ setup_boot()
  │    ├─ writes Termux:Boot script to $HOME/.termux/boot/hive-boot.sh
  │    └─ chmod +x
  └─ create_escape()
       └─ writes brain-plug/escape_living_ai.txt
```

## `install-termux.sh` call graph

```text
main()
  ├─ check_termux()
  ├─ install_packages()
  │    └─ pkg install -y for each of 15 packages
  ├─ setup_repo()
  │    ├─ git pull --depth 1 origin master (if repo exists)
  │    └─ git clone --depth 1 $REPO_URL $INSTALL_DIR
  ├─ link_binaries()
  │    └─ ln -sf each binary into $HOME/bin
  ├─ setup_secure_login()
  │    ├─ sets/reads credentials (password patterns present)
  │    └─ writes secure login files
  ├─ setup_ui()
  │    └─ writes TUI configuration
  └─ setup_boot()
       └─ copies secure boot script to Termux:Boot directory
```

## Reachability from canonical launcher

Neither `install.sh` nor `install-termux.sh` is invoked by the canonical launcher `Hive Ops Final/bin/hive` or by the repository-level dispatcher `bin/hive`. They are standalone entrypoints documented in the README.
