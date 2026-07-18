#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
LOG_DIR="$HOME/hive/logs"
MAX_SIZE=$((1024*1024)) # 1 MiB
KEEP=5
find "$LOG_DIR" -type f -name "*.log" | while read -r f; do
  sz=$(stat -c%s "$f")
  if [ "$sz" -gt "$MAX_SIZE" ] || [ $(find "$f" -mtime +7 -print | wc -l) -gt 0 ]; then
    for i in $(seq $KEEP -1 1); do
      [ -f "$f.$i" ] && mv "$f.$i" "$f.$((i+1))" || true
    done
    mv "$f" "$f.1"
    touch "$f"
  fi
done
find "$LOG_DIR" -type f -name "*.log.*" -mtime +30 -delete
