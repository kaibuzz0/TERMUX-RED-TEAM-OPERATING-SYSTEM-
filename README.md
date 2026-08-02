# 🐍 HIVE OPS DevAI v2.0

> The Answer to the Ultimate Question of Security is **42** (and 45 security components)

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██╗  ██╗██╗██╗   ██╗███████╗     ██████╗ ███████╗          ║
    ║   ██║  ██║██║██║   ██║██╔════╝    ██╔═══██╗██╔════╝          ║
    ║   ███████║██║██║   ██║█████╗      ██║   ██║███████╗          ║
    ║   ██╔══██║██║╚██╗ ██╔╝██╔══╝      ██║   ██║╚════██║          ║
    ║   ██║  ██║██║ ╚████╔╝ ███████╗    ╚██████╔╝███████║          ║
    ║   ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝     ╚═════╝ ╚══════╝          ║
    ║                                                               ║
    ║              🐍 AI↔AI Security System 🐍                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
```

## What's New in v2.0

- 🔐 **Secure Login on Boot** — Password + PIN dual authentication with lockout protection
- 🖥️ **Enhanced Terminal UI** — Full ANSI menu-driven interface with real-time status bar
- 🔄 **One-Line Updates** — `update.sh` pulls latest code, preserves credentials
- 🚑 **Emergency Repair** — `emergency-repair.sh` for when things go wrong
- 📦 **Simplified Termux Install** — `install-termux.sh` handles everything

---

## 📦 Quick Install (Termux)

### One Line (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/master/install-termux.sh | bash
```

### Or Manual Steps

```bash
# 1. Clone
git clone --depth 1 https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git ~/Hive-Ops

# 2. Install
cd ~/Hive-Ops
bash install-termux.sh

# 3. Restart Termux (or source ~/.bashrc)
# Secure login will trigger on next start
```

### What install-termux.sh Does

1. Checks Termux environment
2. Installs dependencies (`git`, `python`, `tor`, `tmux`, `jq`, etc.)
3. Clones this repository
4. Symlinks all `hive-*` binaries to `~/bin`
5. Adds bash integration (`~/.bashrc`)
6. Copies secure boot script to `~/.termux/boot/`
7. **Prompts you to create login credentials** (password + 4-digit PIN)

---

## 🔄 Update Hive OS

Keep your system current without losing credentials:

```bash
cd ~/Hive-Ops
bash update.sh
```

Or from anywhere:

```bash
curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/master/update.sh | bash
```

### What update.sh Does

1. Backs up `~/.hive_auth/` (your login credentials)
2. Backs up `~/.hive_ops.txt` (your notes)
3. Backs up `~/.bashrc`
4. `git fetch` → shows available changes
5. `git pull` latest code
6. Restores credentials and config
7. Re-links binaries
8. Updates boot script

### Force Update (Stash Local Changes)

```bash
bash update.sh --force
```

---

## 🚑 Emergency Repair

When Hive is broken, corrupted, or won't start:

```bash
cd ~/Hive-Ops
bash emergency-repair.sh
```

### Standard Repair (Preserves Credentials)

- Removes old installation
- Re-clones fresh code from GitHub
- **Preserves your login credentials**
- Re-links everything
- Restores boot script

### Full Nuke (⚠️ Destroys Everything)

```bash
bash emergency-repair.sh --full-nuke
```

**Warning:** This deletes `~/.hive_auth/` — you will lose your login credentials and need to create new ones.

---

## 🔐 Secure Login

### First-Time Setup

After installing, restart Termux. You'll see:

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║         🔐 SECURE ACCESS TERMINAL v2.0                         ║
    ╚═══════════════════════════════════════════════════════════════╝

    🔐 First-time setup — create your credentials

    Enter new password: ******
    Confirm password: ******
    Enter 4-digit PIN: ****
    Confirm PIN: ****

    ✅ Credentials saved. Login required on next boot.
```

### Login Screen (Every Boot)

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║         🔐 SECURE ACCESS TERMINAL v2.0                         ║
    ╚═══════════════════════════════════════════════════════════════╝

    ┌───────────────────────────────────────────────────────────────┐
    │  Authentication Required                                        │
    ├───────────────────────────────────────────────────────────────┤
    │  Password: ********                                            │
    │  PIN:      ****                                                │
    └───────────────────────────────────────────────────────────────┘

    ✅ AUTHENTICATION SUCCESSFUL
    🚀 Launching Hive OS...
```

### Security Features

| Feature | Detail |
|---------|--------|
| Dual auth | Password + 4-digit PIN |
| Lockout | 3 failed attempts = 60-second cooldown |
| Logging | All attempts logged to `~/.hive_auth/login.log` |
| Privacy | Screen clears on exit |
| Encryption | Credentials stored base64-encoded (file is chmod 600) |

### Manual Login

```bash
hive-secure-login
# or alias:
hsec
```

---

## 🖥️ Enhanced UI (hive-ui-v2)

Replace the barebones interface with a proper TUI:

```bash
hive-ui-v2
# or alias:
hui
```

### Interface

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║   ██╗  ██╗██╗██╗   ██╗███████╗     ██████╗ ███████╗          ║
    ║   ... (Hive banner) ...                                      ║
    ╚═══════════════════════════════════════════════════════════════╝

    ▸ 🔐 Security
      [1] Firewall Status          [2] Tor / Orbot
      [3] Anomaly Detection        [4] Integrity Check
      [5] Vault

    ▸ 🌐 Network
      [q] Network Mode             [w] New Identity
      [e] Proxy Test               [r] Geo Check

    ▸ 🤖 AI & Swarm
      [a] Swarm Status             [s] Speak (Hermes)
      [d] Agents

    ▸ ⚙️  System
      [z] System Health            [x] Process Monitor
      [c] Services                   [v] Logs
      [b] Doctor (Audit)

    ▸ 💾 Data
      [t] Backup                   [y] Restore
      [u] Rotate Logs

    ─────────────────────────────────────────────────────────────────
    ▸ 🟢 TOR | CPU 12% | MEM 340/1876M | UP 2h14m | 14:32:07

    Press a key to select  |  [Enter] execute  |  [r] refresh  |  [q] quit
```

### Navigation

| Key | Action |
|-----|--------|
| `1–5`, `q–r`, `a–d`, `z–b`, `t–u` | Select menu item |
| `Enter` | Execute command |
| `r` | Refresh screen |
| `q` or `Ctrl+C` | Quit |

### Features

- **Real-time status bar** — Tor status, CPU, memory, uptime, clock
- **Color-coded categories** — Security (red), Network (cyan), AI (magenta), System (green), Data (yellow)
- **Command output** — Shows results, returns to menu on keypress
- **Responsive** — Adapts to terminal size

---

## 🚀 Quick Start Commands

```bash
# System
hive status              # Full system status
hive health              # Health check
hive doctor              # Environment audit
hive ps                  # Process monitor
hive logs                # Tail logs

# Network
hive net status          # Network status
hive net orbot           # Start Tor
hive net newnym          # New identity
hive net test            # Proxy test

# AI & Swarm
hive speak               # Hermes handshake
hive swarm status        # Swarm status
hive agents              # AI agents

# Secure UI
hive-ui-v2               # Enhanced TUI
hive-secure-login        # Manual login

# Aliases (added to ~/.bashrc)
hh    = hive health
hs    = hive status
hd    = hive dashboard
hn    = hive net status
hlog  = hive logs
hps   = hive ps
hui   = hive-ui-v2
hsec  = hive-secure-login
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Boot Layer (Termux:Boot)                     │
│  ~/.termux/boot/00-hive-secure.sh                              │
│  └─ hive-secure-login (password + PIN auth)                    │
│      └─ hive-ui-v2 (enhanced TUI)                              │
├─────────────────────────────────────────────────────────────────┤
│                       OS Layer (hive-os)                        │
│  ├─ hive-ctrl          Unified Controller                      │
│  ├─ hive-gateway       Network Gateway                         │
│  ├─ hive-orchestrator  Autonomous Swarm                        │
│  ├─ hive-agents        AI Agents                               │
│  ├─ hive-42            The Answer                              │
│  └─ hive-hermes        AI Bridge                               │
├─────────────────────────────────────────────────────────────────┤
│                   Security Layer (40 Tools)                   │
│  ├─ Network:  hive-net, hive-firewall, hive-anomaly           │
│  ├─ Crypto:   hive-vault, hive-key, hive-pq                   │
│  ├─ Comms:    hive-comms3, hive-geo                           │
│  ├─ Forensics: hive-forensics, hive-honey, hive-inject        │
│  └─ Ops:      hive-backup, hive-integrity, hive-shred         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Components (45 Total)

### Boot & OS Layer (5)
| Component | Purpose | Command |
|-----------|---------|---------|
| hive-boot | Boot loader with animation | `hive-boot` |
| hive-os | Operating system layer | `hive-os shell` |
| hive-ctrl | Unified controller | `hive-ctrl status` |
| hive-gateway | Network gateway | `hive-gateway status` |
| hive-orchestrator | Autonomous swarm | `hive-orchestrator daemon` |

### UI & Security (2 new)
| Component | Purpose | Command |
|-----------|---------|---------|
| hive-secure-login | Password + PIN auth | `hive-secure-login` |
| hive-ui-v2 | Enhanced TUI | `hive-ui-v2` |

### AI & Integration (2)
| Component | Purpose | Command |
|-----------|---------|---------|
| hive-agents | AI agents framework | Import in Python |
| hive-hermes | Hermes AI bridge | `hive-hermes dashboard` |

### The Answer (1)
| Component | Purpose | Command |
|-----------|---------|---------|
| hive-42 | Ultimate Answer | `hive-42 answer` |

### Security Tools (37)

See full list in original documentation or run `hive --help`.

---

## 🔧 Maintenance Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `install-termux.sh` | Fresh install | First-time setup |
| `update.sh` | Pull latest code | Weekly / when notified |
| `emergency-repair.sh` | Re-install from scratch | Things are broken |
| `install.sh` | Legacy full install | Advanced/manual setup |

---

## ⚙️ Configuration

### Disable Auto-Login

```bash
# Temporarily
export HIVE_BOOT_ENABLE=0

# Permanently
echo 'export HIVE_BOOT_ENABLE=0' >> ~/.bashrc
```

### Change Credentials

```bash
rm -rf ~/.hive_auth
# Restart Termux — setup wizard will run again
```

### Boot Without Secure Login

Replace `~/.termux/boot/00-hive-secure.sh` with the legacy script:

```bash
cp ~/Hive-Ops/Hive\ Ops\ Final/.termux/boot/00-hive-ops.sh ~/.termux/boot/00-hive-secure.sh
```

---

## 📁 File Map

```
~
├── .hive_auth/                    # Login credentials (chmod 700)
│   └── passwd                     # base64-encoded password + PIN
│   └── login.log                  # Login attempt history
│
├── .termux/
│   └── boot/
│       └── 00-hive-secure.sh      # Auto-launch on device boot
│
├── Hive-Ops/                      # Main repo (from GitHub)
│   ├── install-termux.sh          # Termux installer
│   ├── update.sh                  # Update from GitHub
│   ├── emergency-repair.sh        # Nuke + re-install
│   ├── install.sh                 # Legacy installer
│   │
│   ├── Hive Ops Final/
│   │   ├── bin/
│   │   │   ├── hive                # Main command
│   │   │   ├── hive-ui-v2          # Enhanced TUI
│   │   │   ├── hive-secure-login   # Secure login
│   │   │   ├── hive-dashboard      # Legacy dashboard
│   │   │   └── ... (40+ tools)
│   │   ├── .termux/boot/
│   │   │   └── 00-hive-secure.sh   # Boot launcher
│   │   └── etc/
│   │       ├── bash-integration.sh # ~/.bashrc hooks
│   │       └── env.sh              # Environment vars
│   │
│   └── README.md
│
└── bin/                           # Symlinks to Hive tools
    ├── hive → ../Hive-Ops/.../hive
    ├── hive-ui-v2 → ../Hive-Ops/.../hive-ui-v2
    └── ...
```

---

## 🆘 Troubleshooting

### "Secure login not found" on boot

```bash
bash ~/Hive-Ops/Hive\ Ops\ Final/bin/hive-secure-login
# Then re-run installer if needed
bash ~/Hive-Ops/install-termux.sh
```

### "git pull failed" on update

```bash
cd ~/Hive-Ops
bash update.sh --force
# or
bash emergency-repair.sh
```

### Lost credentials

```bash
rm -rf ~/.hive_auth
# Restart Termux — setup will ask for new password + PIN
```

### Boot loop or crash

```bash
# Disable auto-boot temporarily
rm ~/.termux/boot/00-hive-secure.sh
# Fix things manually, then restore
bash ~/Hive-Ops/emergency-repair.sh
```

---

## 🙏 Credits

- **Hive Ops DevAI** — Security system architecture
- **Hermes AI Integration** — AI↔AI bridge protocols
- **Termux Community** — Mobile Linux environment

## 📜 License

Same as upstream. See repository for details.

---

**Don't Panic. The Answer is 42.** 🐍
