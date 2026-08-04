# Root-Enhanced Profile

## Identity

Optional profile for rooted Android devices.

## Requirements

- Rooted device.
- Root access granted to Termux.
- User explicitly enables root-enhanced features.

## Capabilities (optional)

- `iptables` / `nftables` firewall rules.
- Deeper process inspection.
- Mount operations (with caution).
- Enhanced network routing.

## Constraints

- Root modules are separate and disabled by default.
- Clearly labeled as ROOT-ENHANCED.
- Cannot become a silent dependency of standard Hive OS.
- Increases blast radius; use only where necessary.
