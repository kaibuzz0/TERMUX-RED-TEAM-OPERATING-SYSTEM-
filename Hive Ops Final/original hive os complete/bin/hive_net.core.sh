#!/usr/bin/env bash
set -Eeuo pipefail
trap 'code=$?; line=${BASH_LINENO[0]:-UNKNOWN}; cmd=${BASH_COMMAND:-?}; printf "[net] ERROR at line %s: %s (exit %s)\n" "$line" "$cmd" "$code" 1>&2; exit $code' ERR
. "$HOME/.config/hive/env.sh"

MODE_FILE="$HIVE_STATE/net.mode"
SOCKS_ORBOT="${HIVE_TOR_SOCKS_ORBOT}"
SOCKS_LOCAL="${HIVE_TOR_SOCKS_LOCAL}"
CONTROL="${HIVE_TOR_CONTROL}"
TORRC="$HIVE_ETC/tor/torrc"
TORDATA="$HIVE_STATE/tor"
TOR_LOG="$HIVE_LOG/tor.local.log"

log() { printf '[net] %s\n' "$*"; }
write_mode() { printf '%s' "$1" >"$MODE_FILE"; }

read_mode() { if [[ -s "$MODE_FILE" ]]; then cat "$MODE_FILE"; else printf '%s' "${HIVE_PROXY_MODE:-orbot}"; fi; }
socks_host() { printf '%s' "${1%%:*}"; }
socks_port() { printf '%s' "${1##*:}"; }
socks_ok()   { nc -z "$(socks_host "$1")" "$(socks_port "$1")" >/dev/null 2>&1; }
control_ok() { nc -z "$(socks_host "$CONTROL")" "$(socks_port "$CONTROL")" >/dev/null 2>&1; }

cookie_hex() {
  local f="$TORDATA/control_auth_cookie"
  [[ -s "$f" ]] || { echo ""; return 1; }
  if command -v hexdump >/dev/null 2>&1; then
    hexdump -v -e '/1 "%02x"' "$f"
  else
    od -An -v -t x1 "$f" | tr -d ' \n'
  fi
}

ensure_torrc() {
  if [[ ! -f "$TORRC" ]]; then
    mkdir -p "$(dirname "$TORRC")"
    cat >"$TORRC" <<TOR
SOCKSPort ${SOCKS_LOCAL}
ControlPort ${CONTROL}
CookieAuthentication 1
DataDirectory ${TORDATA}
ClientOnly 1
AvoidDiskWrites 1
Log notice file ${TOR_LOG}
TOR
    chmod 600 "$TORRC" || true
  fi
}

start_local() {
  command -v nc   >/dev/null 2>&1 || { log "missing 'nc' (netcat) for checks"; return 1; }
  command -v tor  >/dev/null 2>&1 || { log "missing 'tor' binary; install tor first"; return 1; }
  ensure_torrc
  mkdir -p "$TORDATA"
  if pgrep -x tor >/dev/null 2>&1; then
    log "local tor seems running; skipping start"
  else
    log "starting local tor (SOCKS ${SOCKS_LOCAL}, CONTROL ${CONTROL})…"
    nohup tor -f "$TORRC" >>"$TOR_LOG" 2>&1 &
    sleep 1
  fi
  for _ in $(seq 1 30); do
    socks_ok "$SOCKS_LOCAL" && control_ok && { log "local tor ready."; return 0; }
    sleep 1
  done
  log "local tor not ready (timeout)"; return 1
}

stop_local() {
  if control_ok; then
    hex="$(cookie_hex || true)"
    if [[ -n "${hex:-}" ]]; then
      { printf 'AUTHENTICATE %s\r\nSIGNAL SHUTDOWN\r\nQUIT\r\n' "$hex"; } \
        | nc -w 3 "$(socks_host "$CONTROL")" "$(socks_port "$CONTROL")" >/dev/null 2>&1 || true
      sleep 1
    else
      log "no control cookie; fallback kill"
    fi
  fi
  pkill -x tor >/dev/null 2>&1 || true
}

case "${1:-status}" in
  status)
    m="$(read_mode)"
    case "$m" in
      orbot)
        log "mode=orbot SOCKS=${SOCKS_ORBOT} ControlPort: n/a (orbot)"
        if socks_ok "$SOCKS_ORBOT"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
        ;;
      local)
        log "mode=local SOCKS=${SOCKS_LOCAL} CONTROL=${CONTROL}"
        if socks_ok "$SOCKS_LOCAL"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
        if control_ok; then log "ControlPort reachable."; else log "ControlPort not reachable."; fi
        ;;
      off)
        log "mode=off (network disabled) nominal SOCKS=${SOCKS_ORBOT}"
        if socks_ok "$SOCKS_ORBOT"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
        ;;
    esac
    ;;
  test)
    m="$(read_mode)"; s="$SOCKS_ORBOT"; [[ "$m" == "local" ]] && s="$SOCKS_LOCAL"
    export ALL_PROXY="socks5h://$s"
    log "testing IP via multiple providers (short timeouts)…"
    curl -m 2 -s https://check.torproject.org/api/ip || true
    ;;
  orbot)
    write_mode "orbot"; log "mode set to orbot"
    if socks_ok "$SOCKS_ORBOT"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
    ;;
  local)
    write_mode "local"; log "mode set to local"
    start_local || exit 1
    if socks_ok "$SOCKS_LOCAL"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
    if control_ok; then log "ControlPort reachable."; else log "control port not reachable at ${CONTROL}"; fi
    ;;
  off)
    write_mode "off"; log "mode set to off (net disabled)"
    stop_local || true
    names="$("$HIVE_BIN/hive_services.sh" list)"
    if [[ -n "$names" ]]; then
      "$HIVE_BIN/hive_services.sh" stop $names >/dev/null 2>&1 || true
      log "services stopped (mode=off)"
    else
      log "no services defined to stop"
    fi
    if socks_ok "$SOCKS_ORBOT"; then log "SOCKS reachable."; else log "SOCKS not reachable."; fi
    ;;
  newnym)
    m="$(read_mode)"
    if [[ "$m" != "local" ]]; then log "newnym not available in mode=${m}"; exit 2; fi
    if ! control_ok; then log "ControlPort not reachable."; exit 3; fi
    hex="$(cookie_hex || true)"
    if [[ -z "${hex:-}" ]]; then log "control cookie missing/empty"; exit 4; fi
    resp="$( { printf 'AUTHENTICATE %s\r\nSIGNAL NEWNYM\r\nQUIT\r\n' "$hex"; } \
      | nc -w 3 "$(socks_host "$CONTROL")" "$(socks_port "$CONTROL")" 2>/dev/null || true )"
    if echo "$resp" | grep -q '250 OK'; then
      log "NEWNYM signaled."
    else
      log "NEWNYM failed."; echo "$resp" | sed 's/^/[net-raw] /'; exit 5
    fi
    ;;
  *)
    echo "usage: $(basename "$0") {status|test|orbot|local|off|newnym}"
    exit 64
    ;;
esac
