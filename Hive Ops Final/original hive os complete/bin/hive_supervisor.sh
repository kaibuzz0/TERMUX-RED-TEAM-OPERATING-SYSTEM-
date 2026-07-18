#!/data/data/com.termux/files/usr/bin/bash

# --- ROTATOR LAUNCH BLOCK (auto-injected; idempotent) ---
if ! pgrep -f "hive_rotator\.sh" >/dev/null 2>&1; then
  nohup "/data/data/com.termux/files/home/hive/bin/hive_rotator.sh" >/dev/null 2>&1 &
fi
# --- END ROTATOR LAUNCH BLOCK ---
set -Eeuo pipefail
[ -f "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"
mkdir -p "$HIVE_LOG"
exec "$HIVE_BIN/hive_watchdog.sh" >> "$HIVE_LOG/supervisor.log" 2>&1
  # start rotator sidecar (periodic log rotation)
  if ! pgrep -f "hive_rotator\.sh" >/dev/null 2>&1; then
    nohup "$HIVE_BIN/hive_rotator.sh" >/dev/null 2>&1 &
  fi
