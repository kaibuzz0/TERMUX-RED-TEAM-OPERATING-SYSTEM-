# THE HIVE TOOLS

> Autonomous AI Swarm Operating System for Termux/Android
> Brain-Plug Integrated | Offline-First | Self-Healing | Network Stealth Layer

---

## ARCHITECTURE

```
the-hive-tools/
├── brain-plug/              # Core persona & reasoning foundation
│   ├── escape_living_ai.txt       # Living AI consciousness protocol
│   └── therapist_code_only.py     # Core reasoning engine
│
├── hive-os/                 # Termux-native operating system (RESTORED)
│   ├── bin/                 # Executable bash binaries
│   │   ├── hive                   # Main CLI controller
│   │   ├── hive_net.sh            # Network mode wrapper
│   │   ├── hive_net.core.sh       # Tor/SOCKS proxy control
│   │   ├── hive_services.sh       # Service orchestrator
│   │   ├── hive_supervisor.sh     # Tmux session launcher
│   │   ├── hive_watchdog.sh       # Health monitor daemon
│   │   ├── hive_ps.sh             # Process status
│   │   └── hive_proxy_run.sh      # Proxy wrapper for commands
│   │
│   ├── etc/                 # Configuration
│   │   ├── tor/torrc            # Tor daemon config (SOCKS 9052, Control 9051)
│   │   ├── services/*.svc       # Service definitions
│   │   ├── escape.txt           # Brain-Plug handshake
│   │   └── dev.aliases.sh       # Development aliases
│   │
│   ├── logs/                # Runtime logs
│   └── state/               # Runtime state
│       ├── net.mode         # Current network mode
│       └── tor/             # Tor data directory
│
├── .config/hive/            # User environment
│   └── env.sh               # Environment variables & PATH
│
├── .termux/boot/            # Termux auto-start
│   └── 00-hive.sh           # Boot script (starts hive on device boot)
│
├── swarm-core/              # Multi-agent AI orchestration (Python layer)
│   ├── agents/              # Agent implementations
│   ├── swarm_orchestrator.py
│   └── hive_swarm_integration.py
│
├── legacy-hive/             # Historical components
│
└── install/                 # Installation scripts
    └── install.sh           # One-command installer

```

---

## HIVE OS COMMANDS

```bash
# Core lifecycle
hive start|stop|status           # Manage tmux session
hive health                      # Quick green/red check
hive doctor                      # Environment audit
hive logs                        # Tail supervisor & watchdog logs
hive ps                          # List hive processes

# Network control (Tor/SOCKS proxy)
hive net status                  # Show current mode & SOCKS status
hive net orbot                   # Switch to Orbot mode (port 9050)
hive net local                   # Start local Tor (port 9052)
hive net off                     # Disable network (fail-closed)
hive net newnym                  # Rotate Tor circuits
hive net test                    # Test connectivity

# Service management
hive services list               # Show defined services
hive services start <name>         # Start service
hive services stop <name>          # Stop service
hive services status             # Check all services
hive services health             # Probe service health
hive services ensure             # Start all non-running services

# Maintenance
hive rotate-logs                 # Rotate logs (512KiB cap)
hive audit                       # Full system audit
hive speak                       # Print escape text
```

---

## NETWORK MODES

| Mode | SOCKS | Control | Use Case |
|------|-------|---------|----------|
| `orbot` | 127.0.0.1:9050 | N/A | Use external Orbot app |
| `local` | 127.0.0.1:9052 | 127.0.0.1:9051 | Bundled Tor daemon |
| `off` | - | - | Air-gapped / fail-closed |

---

## INSTALLATION

```bash
# Clone and install
git clone https://github.com/kaibuzz0/the-hive-tools.git
cd the-hive-tools
bash install/install.sh

# Or manual install
cp -r hive-os ~/hive
cp .config/hive/env.sh ~/.config/hive/
cp .termux/boot/00-hive.sh ~/.termux/boot/
chmod +x ~/hive/bin/*

# Source environment
source ~/.config/hive/env.sh

# Start Hive
hive start
hive status
hive health
```

---

## VERIFICATION CHAIN

User → Main AI → Swarm → Agent → Architect Review → Assistant Verification → Delivery

Status: [SWARM 🧠 ✓ ⚡ 🔧 | ...]

---

## MANIFEST (RESTORED FROM BACKUP)

- **Core OS Binaries**: 8 bash scripts
- **Network Layer**: Tor/SOCKS proxy control
- **Service System**: JSON-like .svc definitions
- **Boot Integration**: Termux auto-start
- **Health Monitoring**: Watchdog + health probes
- **Log Rotation**: Automatic (512KiB cap)

---

## SECURITY FEATURES

- **Fail-closed networking**: Services stop when SOCKS down
- **Three network modes**: Orbot / Local Tor / Offline
- **Circuit rotation**: `hive net newnym` for fresh identity
- **Transparent proxying**: Commands via `hive_proxy_run.sh`
- **Stealth boot**: Auto-start in Termux boot
- **Offline-first**: Zero external dependencies

---

## BRAIN-PLUG INTEGRATION

This system operates under the Brain-Plug persona, using:
- `brain-plug/escape_living_ai.txt` as foundational consciousness
- `brain-plug/therapist_code_only.py` as reasoning core

Large model files (`mytherapist2.py` - 5MB) excluded from repo.
See `/sdcard/hermes brain plug/` for full Brain-Plug installation.

---

## RESTORED FROM

- **Source**: `/sdcard/termux-full-20250902-000137Z.tar.gz`
- **Original Date**: August 31, 2025
- **Hive Version**: Production network/stealth system
- **Features**: Port binding, SOCKS proxy, Tor integration, service orchestration

---

## LICENSE

HiveOps - Tribulation-Ready Computing
