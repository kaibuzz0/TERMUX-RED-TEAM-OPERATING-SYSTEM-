#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
[ -f "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"

echo "  PID  PPID %CPU %MEM COMMAND"
pids=$(pgrep -f -d, 'hive_watchdog\.sh|hive_supervisor\.sh|/usr/bin/tor|[t]mux' 2>/dev/null || true)
if [ -n "$pids" ]; then
  if ps --help 2>&1 | grep -q -- '--no-headers'; then
    ps -o pid,ppid,pcpu,pmem,args --no-headers -p "$pids" 2>/dev/null | sort -k3 -nr
  else
    ps -o pid,ppid,pcpu,pmem,args -p "$pids" 2>/dev/null | sed '1d' | sort -k3 -nr
  fi
else
  echo "  (no hive processes matched yet)"
fi
echo
echo "[tmux sessions]"
tmux list-sessions 2>/dev/null || true
