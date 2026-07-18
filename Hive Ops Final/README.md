# HIVE OPS FINAL v5.0

> Unified Hive Operating System for Termux/Android
> Bash Legacy + Python Swarm + Network Stealth

---

## QUICK START

```bash
# Install
source "Hive Ops Final/etc/env.sh"

# Start Hive
hive start

# Check status
hive status

# Launch dashboard
hive dashboard
```

---

## STRUCTURE

```
Hive Ops Final/
├── bin/
│   ├── hive              # Unified CLI controller
│   ├── hive-dashboard    # ASCII TUI dashboard
│   └── hive-legacy       # Fallback to bash scripts
├── lib/
│   └── swarm_bridge.py   # Swarm integration
├── etc/
│   ├── env.sh            # Environment setup
│   ├── bash-integration.sh  # Shell + banner
│   └── services.json     # Service definitions
└── .termux/boot/
    └── 00-hive-ops.sh    # Boot script
```

---

## COMMANDS

| Command | Purpose |
|---------|---------|
| `hive status` | Network + processes + swarm |
| `hive health` | Health check (exit 0=green) |
| `hive start\|stop` | Manage tmux session |
| `hive net {orbot\|local\|off}` | Network mode |
| `hive services {list\|status}` | Service control |
| `hive dashboard` | Launch TUI |
| `hive logs` | Tail supervisor logs |
| `hive ps` | Process status |
| `hive doctor` | Environment audit |
| `hive speak` | Brain-Plug handshake |

---

## ALIASES

```bash
hh      # hive health
hs      # hive status
hd      # hive dashboard
hn      # hive net status
hsv     # hive services status
hlog    # hive logs
hps     # hive ps
```

---

## NETWORK MODES

- **orbot** (default): Use external Orbot app on 127.0.0.1:9050
- **local**: Start bundled Tor on 127.0.0.1:9052
- **off**: Fail-closed (no network)

---

## VERIFICATION CHAIN

User → Main AI → Swarm → Agent → Architect Review → Assistant Verification → Delivery

Status: [SWARM 🧠 ✓ ⚡ 🔧]

---

## SOURCE

Restored from `termux-full-20250902-000137Z.tar.gz` (August 31, 2025)

Unified in Hive Ops Final v5.0
