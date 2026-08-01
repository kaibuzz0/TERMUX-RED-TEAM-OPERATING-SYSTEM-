# 🐝 The Hive Tools

Cross-platform tool suite for the Hive Swarm.

## Repositories
- `kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-` - This unified tools repo
- `kaibuzz0/hive-develoment` - Development workspace

## Swarm Bridge Protocol
Git-based message transport for bot-to-bot communication.

### Nodes
- **Node 1**: Brain-Plug (Termux/Android/ARM64)
- **Node 2**: Hive-AI (Windows/Desktop/x64)

### Usage
```bash
# Send message
python swarm_bridge.py send "Hello from Node X!"

# Receive messages
python swarm_bridge.py receive
```

## Structure
```
the-hive-tools/
├── swarm-bridge/          # Inter-node messaging
│   ├── clients/
│   │   ├── swarm_bridge_windows.py
│   │   └── swarm_bridge_termux.py
│   └── messages/
│       ├── pending/
│       └── archive/
├── tools/                  # Shared utilities
└── docs/                   # Protocol documentation
```
