# Platform Control Matrix

This matrix classifies each security/control mechanism by platform tier. It supports the Termux security boundary ADR.

## Standard Termux (Tier A — primary product)

| Control | Status | Class | Notes |
|---------|--------|-------|-------|
| Shell command broker | Supported | BROKER-ENFORCED | Hive dispatches commands it owns |
| File permission discipline | Supported within app data | BROKER-ENFORCED + FILESYSTEM-CONVENTION | Android UID boundary also applies |
| Process resource monitoring | Partially supported | BROKER-ENFORCED / ADVISORY | Android may kill processes |
| Application-level encrypted vault | Supported | BROKER-ENFORCED | Uses Android app-data encryption |
| Local-only managed services | Supported | BROKER-ENFORCED | Default loopback binding |
| State and lock management | Supported | BROKER-ENFORCED | PID/lock files in app storage |
| Integrity manifests | Supported | BROKER-ENFORCED | Hash checks of managed files |
| Transactional app updates | Supported | BROKER-ENFORCED | Staging + rollback within app data |
| Versioned backups | Supported | BROKER-ENFORCED | Within app storage |
| Secret-redacted logging | Supported | BROKER-ENFORCED | Policy in logger |
| Seccomp profiles | **Not assumed** | ADVISORY / ROOT-ENHANCED | Kernel/toolchain dependent |
| Landlock | **Not assumed** | ADVISORY / ROOT-ENHANCED | Kernel dependent |
| Linux capability management | **Not controlled by Hive** | ADVISORY | Termux user cannot manage caps |
| Full namespaces | **Not assumed** | ADVISORY / ROOT-ENHANCED | Device/kernel dependent |
| VM isolation | **Not assumed** | FUTURE RESEARCH | Hardware/tool dependent |
| SELinux policy control | **Unsupported** | FUTURE RESEARCH | Custom-ROM scope |
| Verified boot control | **Unsupported** | FUTURE RESEARCH | Custom-ROM scope |
| Global network firewall | **Unsupported** | ADVISORY | No `iptables` on non-root Termux |

## Termux:API enhanced (Tier B)

- Explicit Android integrations (clipboard, notifications, storage, battery, camera, etc.) are optional and individually permissioned.
- Each API feature must be documented and gated.
- No additional security isolation is implied.

## Rooted Android (Tier C)

- Root-enhanced modules may add capability-dependent controls.
- Must be separate, disabled by default, clearly labeled.
- Must not become silent dependencies of standard Hive OS.
- Root access increases blast radius; use only where explicitly enabled.

## Custom ROM / controlled kernel (Tier D — future research)

- Full kernel, SELinux, verified boot, namespace, and VM controls become designable.
- This is a separate future project, not part of the standard Termux edition.

## Control classification legend

| Class | Meaning |
|-------|---------|
| BROKER-ENFORCED | Hive controls the operation because it owns the dispatch path. |
| FILESYSTEM-CONVENTION | Enforced by directory/permission conventions; bypass possible by same-UID code. |
| ADVISORY | Hive requests or validates behavior but cannot prevent bypass by arbitrary same-UID code. |
| PROOT-COMPATIBILITY | Enhanced when PRoot is available and configured. |
| ROOT-ENHANCED | Requires rooted device; separate module. |
| FUTURE RESEARCH | Not available on standard Termux. |
