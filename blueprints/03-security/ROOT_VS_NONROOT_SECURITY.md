# Root vs Non-Root Security

## Standard non-root Termux (Tier A)

### What Hive OS can provide

- User-space command dispatch and policy.
- File organization and permission discipline.
- Local-only services bound to loopback.
- Process supervision within Termux.
- Encrypted Termux app data (Android-level).
- Backup and recovery of application files.
- Auditing within the app.
- Integrity checking of installed files (hash manifests).
- Workspace organization via directories + environment restrictions.

### What Hive OS cannot provide on non-root Termux

- Kernel isolation or VM-level compartments.
- Global Android SELinux policy changes.
- Verified boot control.
- Replacement Android lock screen.
- Full-device authentication.
- Global firewall / packet filter.
- Guaranteed isolation from other Termux UID processes.
- Persistent background execution guarantee (Android may kill Termux).

## Rooted Android (Tier C)

### Additional capabilities possible

- Write to `/data/data/com.termux` of other apps? No — still Android UID isolation.
- Modify system partitions? Only with unlocked bootloader / custom recovery.
- Run `iptables`? Yes, but root modules must be clearly separated and disabled by default.
- Access `/proc/<pid>` of other apps? Some visibility, but not full isolation bypass.

### Risks

- Root access increases blast radius if Hive OS is compromised.
- Root modules can become silent dependencies of standard features.
- Root-hide/root-detection games are an arms race.

## Current repository separation

| Feature | Root-specific file? | Disabled by default? | Notes |
|---------|---------------------|----------------------|-------|
| `/root/hive` paths in `Hive Ops Final/bin/hive` | No | N/A | Will fail on non-root Termux |
| Root-specific scripts | Not identified yet | Unknown | Requires deeper inspection |

## Recommendations for target architecture

1. Separate root-enhanced capabilities into optional `root.d/` or `root-enhanced/` modules.
2. Non-root code must never depend on root-only behavior.
3. Clearly label every command as `STANDARD`, `ROOT-ENHANCED`, `CUSTOM-ROM`, or `HARDWARE-DEPENDENT`.
4. Do not advertise root features as standard security.
