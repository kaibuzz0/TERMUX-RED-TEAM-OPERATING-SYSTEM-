# Standard Termux Profile

## Identity

Primary supported product. Requires no root.

## Capabilities

- Private app-storage layout.
- Safe path handling.
- Command approval through Hive.
- Hermes task scope validation.
- Application-level encrypted vault.
- Local-only managed services.
- Process tracking for Hive-managed processes.
- State and lock management.
- Integrity manifests.
- Transactional application updates.
- Versioned backups.
- Secret-redacted logging.
- Workspace management with directory conventions.

## Explicitly not provided

- Kernel containment.
- Global network firewall policy.
- Android SELinux changes.
- Android boot-chain trust.
- Isolation from arbitrary same-UID Termux processes.
- Guaranteed survival of Android process termination.
- Hardware virtual machines.
- Full Linux capability control.

## Control classification

All controls in this profile are BROKER-ENFORCED, FILESYSTEM-CONVENTION, or ADVISORY. No ROOT-ENHANCED or FUTURE RESEARCH controls are active.
