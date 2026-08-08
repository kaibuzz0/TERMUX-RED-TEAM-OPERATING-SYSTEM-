# Milestone 18 Device Baseline

## Environment Classification
**NOT native Termux.** This is a PRoot-distro (Debian/Ubuntu-like) running inside Termux.
The system is an Android 16 host with a Linux container layer.

## Device Information
- Manufacturer: samsung
- Model: SM-A156U
- Android Version: 16
- Kernel: Linux localhost 6.17.0-PRoot-Distro #1 SMP PREEMPT_DYNAMIC aarch64 GNU/Linux
- CPU ABI: arm64-v8a
- Architecture: aarch64

## Memory
- Total RAM: ~3.5 GB (3644192 kB)
- Available: ~883 MB
- Swap: 8.0 GB total, 5.9 GB free

## Storage
- Filesystem: /dev/block/dm-62
- Size: 106 GB
- Used: 76 GB (72%)
- Available: 31 GB

## Software Versions
- Python: 3.11.2 (main, GCC 12.2.0) [system python3]
               3.14.6 [termux python]
- Bash: 5.2.15(1)-release (aarch64-unknown-linux-gnu)
- Git: 2.39.5
- OpenSSL: 3.0.20
- cryptography: 50.0.0 (installed in venv)
- pytest: 9.1.1 (installed in venv)
- termux-tools: 1.45.0

## Termux Context
- User: root (inside PRoot)
- HOME: $HOME (PRoot root, not native Termux)
- PREFIX: (empty in PRoot)
- TMPDIR: (empty in PRoot; set to /tmp for testing)
- Termux:API: Not tested (command timed out)
- Termux plugin: com.termux.nix versionCode:188037
- PRoot: YES (kernel string confirms PRoot-Distro)

## Root Status
- Running as root (uid=0)
- This is root inside proot, not Android root

## Security Notes
- No IMEI, serial, Android ID, phone number, or credentials recorded.
- No real user data paths exposed.
