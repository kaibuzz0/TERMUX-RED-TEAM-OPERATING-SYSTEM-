# Battery and Thermal Model

## Default behavior

- No wake locks by default.
- No background polling by default.
- Services default to foreground-only unless explicitly enabled.

## Optional behaviors

- Wake lock for a specific long-running task (requires Termux:API).
- Run-while-charging for heavy tasks.
- Thermal-aware throttling by delegating to Android.

## Measurement

- `hive system health` reports battery/thermal status if Termux:API available.
- Agent tasks report CPU time and memory usage.
