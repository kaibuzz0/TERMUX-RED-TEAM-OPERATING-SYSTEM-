# Milestone 18 Device Baseline

## Repository Baseline

- Branch: `master`
- Commit tested: `7da6b02`
- CI status: all six jobs green (verified for commit 7da6b02)
- Local tests: 529 passed, 8 skipped

## Android/Termux Agent Access Check

This Windows-hosted Hermes agent does **not** have access to a real Android/Termux environment:

- `adb.exe`: not found on PATH or common locations
- `ssh 127.0.0.1:22`: connection timed out
- `TERMUX_VERSION`: not set in current environment
- `ANDROID_ROOT`: not set
- `PREFIX`: not set
- `TMPDIR`: not set
- Current OS: Windows 10 (Microsoft Windows [Version 10.0.26100.8875])

Milestone 18 requires physical Android/Termux evidence. A Windows-hosted agent cannot complete it.

## Required Device Information (to be filled by on-device agent or user)

- Android version:
- Device make/model:
- Architecture / CPU ABI:
- RAM:
- Free internal storage:
- Termux version/source:
- Python version:
- Bash version:
- Git version:
- OpenSSL version:
- cryptography version:
- HOME:
- PREFIX:
- TMPDIR:
- root/non-root:
- Termux:API availability:
- PRoot availability:
- Charging state:
- Starting battery percentage:
- Thermal status if measurable:

## Prohibited from recording

- IMEI
- Android ID
- Serial number
- Phone number
- Account identity
- Personal tokens
- Private credentials
