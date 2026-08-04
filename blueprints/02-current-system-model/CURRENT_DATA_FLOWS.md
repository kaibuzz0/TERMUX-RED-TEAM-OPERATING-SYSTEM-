# Current Data Flows

**Static model.** Runtime behavior is **UNVERIFIED ON TERMUX**.

## Credential flow

```text
User keyboard (Termux)
    → install-termux.sh / emergency-repair.sh --full-nuke / hive-secure-login
        → read password+PIN
            → concatenate with newline
                → base64
                    → write ~/.hive_auth/passwd
                        → chmod 600
```

**Observations:**
- No hashing, no salt, no key derivation.
- File is only protected by Unix permissions (Android app-UID scope).
- Any process running under the same Android UID can read it.

## Update flow

```text
User runs update.sh
    → mkdir ~/.hive_backup/<ts>
        → cp -r ~/.hive_auth ~/.hive_backup/<ts>/
        → cp ~/.hive_ops.txt ~/.hive_backup/<ts>/
        → cp ~/.bashrc ~/.hive_backup/<ts>/
    → cd ~/Hive-Ops
        → git fetch origin master
        → git rev-parse HEAD vs origin/master
        → if behind: git pull origin master
            → (force mode: git stash before pull)
    → cp -r ~/.hive_backup/<ts>/.hive_auth ~/
    → chmod ~/.hive_auth
    → relink Hive Ops Final/bin/hive* into ~/bin
    → copy 00-hive-secure.sh to ~/.termux/boot/
```

**Observations:**
- No rollback image retained automatically.
- No verification of downloaded code.
- Local uncommitted changes stashed silently in `--force` mode.

## Repair flow

```text
User runs emergency-repair.sh
    → ask confirmation
    → mkdir ~/.hive_rescue/
        → cp -r ~/.hive_auth ~/.hive_rescue/
        → cp ~/.hive_ops.txt ~/.hive_rescue/
        → cp ~/.bashrc ~/.hive_rescue/bashrc.backup
    → rm -rf ~/Hive-Ops
    → rm -rf ~/bin/hive*
    → rm -f ~/.termux/boot/00-hive*
    → git clone --depth 1 origin master ~/Hive-Ops
    → restore credentials
    → relink + re-copy boot script
```

**Observations:**
- Requires network.
- Unquoted globs.
- `--full-nuke` has possible control-flow bug (see critical finding validation).

## Install flow

```text
User runs install-termux.sh
    → check_termux()
    → pkg update && pkg install ...
    → git clone into ~/Hive-Ops
    → mkdir ~/bin
    → for each ~/Hive-Ops/Hive Ops Final/bin/hive*:
        ln -sf $bin ~/bin/$name
    → append PATH to ~/.bashrc
    → source bash-integration.sh in ~/.bashrc
    → copy 00-hive-secure.sh to ~/.termux/boot/
    → prompt password+PIN → base64 → ~/.hive_auth/passwd
```

## Boot flow

```text
Android starts / Termux:Boot app triggers
    → ~/.termux/boot/00-hive-secure.sh
        → hive-secure-login
            → clear screen, draw banner
            → read password+PIN
            → base64 decode ~/.hive_auth/passwd
            → compare
            → 3-fail lockout (60s)
            → on success, clear screen and run hive-ui-v2
```

## Network flow

```text
hive net orbot
    → external Orbot proxy 127.0.0.1:9050 (UNVERIFIED)
hive net local
    → bundled Tor on 127.0.0.1:9052 (UNVERIFIED)
hive net off
    → fail-closed (UNVERIFIED)
```

## Hermes integration flow (intended)

```text
install.sh writes
    HERMES_HIVE_MODE="assist"
    HERMES_HIVE_BRIDGE="$HIVE_HOME/shared/bridge.sock"
    into ~/.config/hive/env.sh

Hermes Plugins/install.sh copies
    Hive-Ops plugin skeleton into ~/.hermes/plugins/hive-ops-plugin/
        __init__.py
        brain_plug.py
        agents/__init__.py
        plugin.json
```

**Observations:**
- No evidence of runtime tool registration via `ctx.register_tool(...)`.
- No evidence of skill manifest.
- Plugin reachability **UNVERIFIED**.
