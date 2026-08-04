# Policy Engine Specification

## Scope

The policy engine is a user-space authorization and command-routing component. It enforces policy over operations that pass through Hive. It does **not** claim to contain arbitrary programs running under the same Android application UID.

## Control classes

| Class | Definition | Examples |
|-------|------------|----------|
| BROKER-ENFORCED | Hive controls the operation because it owns the dispatch path. | `hive agent run`, `hive service start`, `hive workspace create` |
| FILESYSTEM-CONVENTION | Enforced by directory/permission conventions; bypass possible by same-UID code. | Workspace directory isolation, vault file permissions |
| ADVISORY | Hive requests or validates behavior but cannot prevent bypass by arbitrary same-UID code. | Global network egress, direct shell execution by operator |
| PROOT-COMPATIBILITY | Enhanced when PRoot is available and configured. | PRoot workspace isolation |
| ROOT-ENHANCED | Requires rooted device. | `iptables`-based firewall rules |
| FUTURE RESEARCH | Not available on standard Termux. | VM isolation, SELinux policy control |

## Policy rules

1. **Command registry:** every `hive` subcommand is registered with required permissions and control class.
2. **Path validation:** all paths are resolved to absolute form and checked against allowlists.
3. **Network policy:** network mode per task/workspace: `deny`, `mirror`, or explicit allowlist.
4. **Secret policy:** secrets never leave the vault as raw values; agents receive capabilities.
5. **Approval policy:** destructive, security-critical, and network-opening operations require confirmation.
6. **Audit policy:** every policy decision is logged with redacted details.

## Policy enforcement points

| Point | Enforces |
|-------|----------|
| CLI dispatcher | Command existence, global options, JSON mode |
| Lock manager | Concurrent destructive-op exclusion |
| Config validator | Allowed values and schema |
| Workspace manager | Path scoping |
| Agent broker | Task manifest compliance |
| Service supervisor | Service manifest compliance, listener address |
| Vault | Secret access rules |
| Network module | Listener reporting (advisory) |

## Bypass acknowledgment

- Direct shell execution by the operator is outside the Hive policy boundary.
- A malicious Python process launched outside Hive is not contained by the policy engine.
- Global device network egress is not enforceable by standard Hive.
- These limitations are documented and not hidden.

## Failure mode

- Policy violation → operation rejected, security event logged.
- Policy engine unavailable → fail closed (read-only mode where possible).
