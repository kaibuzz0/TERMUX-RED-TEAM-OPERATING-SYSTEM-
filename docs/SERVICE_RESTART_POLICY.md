# Service Restart Policy

Policies:

- `never` (default)
- `on-failure`
- `always`
- `unless-stopped`

Back-off is exponential with a configured maximum. After `max_attempts` within `window_seconds`, a service enters `CRASH_LOOP` and requires manual `hive service reset`.
