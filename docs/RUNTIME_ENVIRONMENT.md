# Hive OS Runtime Environment

**Milestone 3 — Runtime Capability Detection and Path Model**

## Supported platforms

| Platform | Status |
|----------|--------|
| Android / Termux | Primary target; unverified until physical test |
| Desktop Linux | Secondary target; static design only so far |
| Windows | Static test host only; not a runtime target |

## Path model

Hive OS uses the following state directory model on Unix-like platforms:

| Purpose | Path |
|---------|------|
| User configuration | `$HOME/.config/hive` |
| State data | `$HOME/.local/state/hive` |
| User data | `$HOME/.local/share/hive` |
| Cache | `$HOME/.cache/hive` |
| Runtime data (Termux) | `$PREFIX/var/run/hive` |

On Termux:

- `$HOME` is typically `/data/data/com.termux/files/home`.
- `$PREFIX` is typically `/data/data/com.termux/files/usr`.

## Prohibited assumptions

The following paths must not be assumed at runtime:

- `/root/hive`
- `/root/`
- `/usr/local`
- `/opt/hive`
- Windows drive letters (`C:\`)
- A specific username
- A specific working directory

## Capability states

The runtime detector reports capabilities using explicit states:

| State | Meaning |
|-------|---------|
| `AVAILABLE` | Confirmed present |
| `UNAVAILABLE` | Confirmed absent |
| `UNKNOWN` | Cannot determine |
| `UNVERIFIED` | Not checked or not checkable on this host |
| `NOT_APPLICABLE` | Does not apply to this platform |

## Invocation commands

```text
hive --resolve          # Show launcher resolution
hive --runtime-info     # Human-readable runtime summary
hive --runtime-info --json  # Structured runtime report
```

These commands are read-only and do not mutate configuration or data.

## Windows qualification

All Milestone 3 results on the Windows host are **STATICALLY VERIFIED ON WINDOWS**. Actual Termux behavior must be validated on a physical Android device.


## Environment overrides

| Variable | Purpose |
|----------|---------|
| `HIVE_HOME` | Legacy install root (used by env.sh) |
| `HIVE_OS_ROOT` | OS data root replacement for `/root/hive-os` |
| `HIVE_SWARM_ROOT` | Swarm data root replacement for `/root/hive-swarm` |
| `HIVE_CONFIG_ROOT` | Configuration root |
| `HIVE_STATE_ROOT` | Mutable state root |
| `HIVE_DATA_ROOT` | Persistent data root |
| `HIVE_CACHE_ROOT` | Cache root |
| `HIVE_LOG_ROOT` | Log root |
| `HIVE_TEMP_ROOT` | Temporary root |

Relative override values are rejected.
