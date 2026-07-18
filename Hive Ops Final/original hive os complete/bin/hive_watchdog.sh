#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; line=${BASH_LINENO[0]:-UNKNOWN}; cmd=${BASH_COMMAND:-?}; printf "%s %s\n" "$(date "+%F %T")" "watchdog ERROR at line ${line}: ${cmd} (exit ${code})" 1>&2; exit $code' ERR
. "$HOME/.config/hive/env.sh"

MODE_FILE="$HIVE_STATE/net.mode"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*"; }
read_mode() { [[ -s "$MODE_FILE" ]] && cat "$MODE_FILE" || printf '%s' "${HIVE_PROXY_MODE:-orbot}"; }

socks_host() { printf '%s' "${1%%:*}"; }
socks_port() { printf '%s' "${1##*:}"; }
socks_ok()   { nc -z "$(socks_host "$1")" "$(socks_port "$1")" >/dev/null 2>&1; }

active_socks() {
  case "$(read_mode)" in
    local) printf '%s' "${HIVE_TOR_SOCKS_LOCAL}" ;;
    orbot) printf '%s' "${HIVE_TOR_SOCKS_ORBOT}" ;;
    off)   printf '%s' "${HIVE_TOR_SOCKS_ORBOT}" ;;
  esac
}

rotate_logs() {
  # 512 KiB cap; keep perms 600 after truncation
  for f in "$HIVE_LOG"/*.log; do
    [ -f "$f" ] || continue
    sz=$(wc -c <"$f" 2>/dev/null || echo 0)
    if [ "$sz" -gt $((512*1024)) ]; then
      mv "$f" "$f.$(date +%Y%m%d-%H%M%S)"
      : >"$f"
      chmod 600 "$f" 2>/dev/null || true
      log "[rotate] $f rotated"
    fi
  done
}

iter=0
while true; do
  mode="$(read_mode)"
  socks="$(active_socks)"
  if [[ "$mode" == "off" ]]; then
    names="$("$HIVE_BIN/hive_services.sh" list)"
    if [[ -n "$names" ]]; then
      "$HIVE_BIN/hive_services.sh" stop $names >/dev/null 2>&1 || true
      log "mode=off, holding services stopped"
    else
      log "mode=off, no services defined"
    fi
    sleep 5
    iter=$((iter+1))
    [[ $((iter % 20)) -eq 0 ]] && rotate_logs
    continue
  fi

  if socks_ok "$socks"; then
    log "socks OK at $socks"
    if [[ "${HIVE_AUTOSTART_SERVICES:-0}" -eq 1 ]]; then
      "$HIVE_BIN/hive_services.sh" ensure >/dev/null 2>&1 || true
    else
      "$HIVE_BIN/hive_services.sh" health >/dev/null 2>&1 || true
    fi
  else
    log "socks DOWN at $socks — stopping net services"
    names="$("$HIVE_BIN/hive_services.sh" list)"
    [[ -n "$names" ]] && "$HIVE_BIN/hive_services.sh" stop $names >/dev/null 2>&1 || true
  fi

  sleep 15
  iter=$((iter+1))
  [[ $((iter % 20)) -eq 0 ]] && rotate_logs
done
