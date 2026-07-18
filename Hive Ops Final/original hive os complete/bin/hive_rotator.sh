#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
HIVE_LOGS="${HIVE_LOGS:-$HOME/hive/logs}"
HIVE_BIN="${HIVE_BIN:-$HOME/hive/bin}"
umask 077
mkdir -p "$HIVE_LOGS"
touch "$HIVE_LOGS/rotator.touch" 2>/dev/null || true

while :; do
  "$HIVE_BIN/hive_logrotate.sh" >/dev/null 2>&1 || true
  # heartbeat so audits can confirm freshness
  date +%s > "$HIVE_LOGS/rotator.touch" 2>/dev/null || true
  sleep 300
done
