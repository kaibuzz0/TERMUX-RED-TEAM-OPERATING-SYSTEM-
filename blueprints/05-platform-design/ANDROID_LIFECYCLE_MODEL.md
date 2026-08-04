# Android Lifecycle Model

## Termux process lifecycle

```text
User opens Termux
    → shell starts
    → optional session gate triggers
    → user operates Hive
    → Android may kill Termux at any time due to memory pressure
    → on restart, session gate triggers again if Termux:Boot is not used

Device boot with Termux:Boot
    → Termux:Boot app runs ~/.termux/boot/ scripts
    → Hive session gate may trigger
    → process may be killed by Android later
```

## Implications

- No persistent background service is guaranteed.
- State must be persisted to disk, not held in memory.
- Services must handle restart gracefully.
- Wake locks are optional and require Termux:API permission.
- Long-running tasks should checkpoint.

## Battery and thermal

- Android may throttle or kill Termux under thermal/load pressure.
- Hive should not assume continuous CPU availability.
- Optional run-while-charging policies for heavy tasks.
