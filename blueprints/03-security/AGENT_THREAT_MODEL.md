# Agent Threat Model

## Current agent components

| Component | Source | Claimed behavior |
|-----------|--------|------------------|
| `hive-orchestrator.py` | `Hive Ops DevAI/` | Recursive agent spawning, self-healing, autonomous task decomposition, consensus |
| `hive_agents.py` | `Hive Ops DevAI/` | Multi-specialized agents (security, crypto, network, forensics, intelligence, swarm) |
| `swarm_orchestrator.py` | both DevAI and Final | Swarm orchestration |
| `swarm_pet.py` | both DevAI and Final | Companion / pet agent |
| `Hive Ops Final/lib/swarm_bridge.py` | Final | Bridge to swarm |
| `Hive Ops DevAI/bin/hive-hermes` | DevAI | Hermes bridge command |
| `Hive Ops DevAI/bin/hivedev-swarm*` | DevAI | Swarm tools |

## Threats

### AT1 — Recursive delegation explosion

- **Actor:** orchestrator or any agent.
- **Entry point:** `hive-orchestrator.py` `daemon` mode.
- **Weakness:** source advertises recursive spawning without stated depth limit.
- **Impact:** resource exhaustion, runaway tasks, bill/cost explosion if using paid models.
- **Mitigation:** hard maximum delegation depth, budget caps, approval for spawning.

### AT2 — Agent escapes allowed paths

- **Actor:** agent tool execution.
- **Weakness:** no evidence of scoped read/write paths in current code.
- **Impact:** reads `~/.hive_auth`, modifies `~/.bashrc`, deletes user files.
- **Mitigation:** allowed-path lists, toolset restrictions, mandatory approvals for destructive ops.

### AT3 — Agent executes remote code

- **Actor:** agent generates commands.
- **Weakness:** tools can run shell commands; no verification step.
- **Impact:** malicious update, data exfiltration.
- **Mitigation:** forbid agents from running installers/updaters; require human approval.

### AT4 — Agent impersonates operator

- **Actor:** agent with access to credentials.
- **Weakness:** no separate identity for agents.
- **Impact:** actions attributed to operator, audit log confusion.
- **Mitigation:** agent-specific identity tokens, no access to operator secrets.

### AT5 — Swarm consensus failure / Byzantine agent

- **Actor:** one compromised sub-agent.
- **Weakness:** advertised "Byzantine fault tolerance" and "consensus" without evidence of implementation.
- **Impact:** false consensus, bad decisions.
- **Mitigation:** remove unimplemented claims; design bounded voting if needed.

### AT6 — Persistent autonomous loops

- **Actor:** orchestrator daemon.
- **Weakness:** can run indefinitely.
- **Impact:** battery drain, thermal issues, unexpected network usage on mobile.
- **Mitigation:** explicit daemon lifetime, sleep/idle policy, operator stop command.

## Required controls for target architecture

1. Maximum delegation depth and child count.
2. Per-task allowed read/write/network scope.
3. Toolset allowlist; no installer/update tools for agents.
4. Human approval for destructive, network, and secret-using operations.
5. Separate agent identity and audit trail.
6. Kill switch / `hive agent halt` command.
7. No autonomous loops without explicit operator opt-in and duration.
