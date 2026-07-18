#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
HIVE_BIN="${HIVE_BIN:-$HOME/hive/bin}"
sub="${1:-}"

# Delegate to the original implementation
"$HIVE_BIN/hive_net.core.sh" "$@"

# Post-hook for mode switches: orbot/local/off
case "$sub" in
  orbot|local|off)
    echo "[hive_net] Auto-ensure services after mode switch..."
    "$HIVE_BIN/hive_services.sh" ensure || true
    for i in 1 2 3 4 5; do
      if "$HIVE_BIN/hive_services.sh" health >/dev/null 2>&1; then
        echo "[hive_net] Health green after $i retries."
        break
      fi
      sleep 1
    done
  ;;
esac
