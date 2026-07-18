#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; line=${BASH_LINENO[0]:-UNKNOWN}; cmd=${BASH_COMMAND:-?}; printf "[services] ERROR at line %s: %s (exit %s)\n" "$line" "$cmd" "$code" 1>&2; exit $code' ERR
. "$HOME/.config/hive/env.sh"

MODE_FILE="$HIVE_STATE/net.mode"
SERV_DIR="$HIVE_ETC/services"

log() { printf '[services] %s\n' "$*"; }
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

# Exclude files that start with "_" (e.g., _TEMPLATE.svc)
list() {
  ( cd "$SERV_DIR" 2>/dev/null || exit 0
    for f in *.svc; do
      [ -e "$f" ] || continue
      b=${f%.svc}
      [[ "$b" == _* ]] && continue
      printf '%s\n' "$b"
    done
  ) || true
}

describe() { local n="$1"; [[ -f "$SERV_DIR/$n.svc" ]] && cat "$SERV_DIR/$n.svc"; }

pid_of() { pgrep -f -u "$(id -u)" -- "$1" 2>/dev/null || true; }

start_one() {
  local name="$1" file="$SERV_DIR/$1.svc"
  [[ -f "$file" ]] || { log "$name not defined"; return 1; }
  # shellcheck disable=SC1090
  . "$file"
  : "${START:?missing START}"
  : "${LOG:=$HIVE_LOG/$name.log}"
  : "${REQUIRES_NET:=1}"
  : "${USE_PROXY_ENV:=0}"
  : "${WANT_TORSOCKS:=0}"

  local mode socks; mode="$(read_mode)"; socks="$(active_socks)"
  if [[ "$mode" == "off" && "$REQUIRES_NET" -eq 1 ]]; then
    log "$name: not starting (mode=off)"; return 2
  fi
  if [[ "$REQUIRES_NET" -eq 1 ]] && ! socks_ok "$socks"; then
    log "$name: not starting (SOCKS down at $socks)"; return 3
  fi

  if pid=$(pid_of "$START"); [[ -n "${pid:-}" ]]; then
    log "$name: already running (pid ${pid})"; return 0
  fi

  log "$name: starting…"
  if [[ "$USE_PROXY_ENV" -eq 1 || "$WANT_TORSOCKS" -eq 1 ]]; then
    USE_PROXY_ENV="$USE_PROXY_ENV" WANT_TORSOCKS="$WANT_TORSOCKS" \
      nohup "$HIVE_BIN/hive_proxy_run.sh" -- "$START" >>"$LOG" 2>&1 &
  else
    nohup bash -lc "$START" >>"$LOG" 2>&1 &
  fi

  sleep 1
  if pid=$(pid_of "$START"); [[ -n "${pid:-}" ]]; then
    log "$name: started (pid ${pid})"
  else
    log "$name: failed to start"
    return 4
  fi
}

stop_one() {
  local name="$1" file="$SERV_DIR/$1.svc"
  [[ -f "$file" ]] || return 0
  # shellcheck disable=SC1090
  . "$file"
  : "${START:?missing START}"
  local killed=false
  if pids="$(pid_of "$START")" && [[ -n "${pids:-}" ]]; then
    log "$name: stopping (pids ${pids})"
    pkill -f -- "$START" || true
    killed=true
  fi
  for _ in 1 2 3 4 5; do
    sleep 1
    pids="$(pid_of "$START")"
    [[ -z "${pids:-}" ]] && break
  done
  if pids="$(pid_of "$START")" && [[ -n "${pids:-}" ]]; then
    log "$name: force killing (pids ${pids})"
    pkill -9 -f -- "$START" || true
  elif [[ "$killed" == true ]]; then
    log "$name: stopped"
  fi
}

status_one() {
  local name="$1" file="$SERV_DIR/$1.svc"
  [[ -f "$file" ]] || { log "$name: not defined"; return 1; }
  # shellcheck disable=SC1090
  . "$file"
  : "${START:?missing START}"
  if pid=$(pid_of "$START"); [[ -n "${pid:-}" ]]; then
    log "$name: running (pid ${pid})"
  else
    log "$name: stopped"; return 3
  fi
}

probe_one() {
  local name="$1" file="$SERV_DIR/$1.svc"
  [[ -f "$file" ]] || return 0
  # shellcheck disable=SC1090
  . "$file"
  if [[ -n "${PROBE:-}" ]]; then
    if bash -lc "$PROBE" >/dev/null 2>&1; then
      log "$name probe: OK"
    else
      log "$name probe: FAIL"; return 2
    fi
  fi
}

case "${1:-help}" in
  list) list ;;
  describe) describe "${2:?name}";;
  start) shift; for s in "$@"; do start_one "$s"; done ;;
  stop)  shift; for s in "$@"; do stop_one  "$s"; done ;;
  status)
    shift; set -- $(list)
    for s in "$@"; do status_one "$s" || true; done
    ;;
  health)
    failed=0
    socks="$(active_socks)"
    if ! socks_ok "$socks"; then log "SOCKS down at $socks"; failed=1; fi
    set -- $(list)
    for s in "$@"; do probe_one "$s" || failed=1; done
    exit "$failed"
    ;;
  ensure)
    set -- $(list)
    for s in "$@"; do start_one "$s" || true; done
    ;;
  *)
    echo "usage: $(basename "$0") {list|describe|start|stop|status|health|ensure}"
    exit 64
    ;;
esac
