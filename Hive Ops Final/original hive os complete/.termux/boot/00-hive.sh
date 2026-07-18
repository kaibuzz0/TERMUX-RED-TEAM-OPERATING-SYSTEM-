#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
umask 077
# Minimal boot wrapper — honors HIVE_BOOT_ENABLE=1
ENV_FILE="$HOME/.config/hive/env.sh"
[ -r "$ENV_FILE" ] && . "$ENV_FILE"
: "${HIVE_BIN:=$HOME/hive/bin}"
: "${HIVE_BOOT_ENABLE:=1}"
if [[ "$HIVE_BOOT_ENABLE" != "1" ]]; then
  echo "[boot] Hive boot disabled (HIVE_BOOT_ENABLE=$HIVE_BOOT_ENABLE)"
  exit 0
fi
if tmux has-session -t hive 2>/dev/null; then
  echo "[boot] Hive already running; skip."
  exit 0
fi
exec "$HIVE_BIN/hive" start
