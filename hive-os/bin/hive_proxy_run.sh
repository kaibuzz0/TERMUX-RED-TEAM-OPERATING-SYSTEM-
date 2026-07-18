#!/usr/bin/env bash
# Usage: (env USE_PROXY_ENV=1 WANT_TORSOCKS=0) hive_proxy_run.sh -- <cmd string>
set -Eeuo pipefail
trap 'code=$?; line=${BASH_LINENO[0]:-UNKNOWN}; cmd=${BASH_COMMAND:-?}; echo "[proxy] ERROR at line ${line}: ${cmd} (exit ${code})"; exit $code' ERR
. "$HOME/.config/hive/env.sh"

MODE_FILE="$HIVE_STATE/net.mode"
read_mode() { [[ -s "$MODE_FILE" ]] && cat "$MODE_FILE" || printf '%s' "${HIVE_PROXY_MODE:-orbot}"; }
socks_of_mode() {
  case "$(read_mode)" in
    local) printf '%s' "${HIVE_TOR_SOCKS_LOCAL}" ;;
    orbot|off|*) printf '%s' "${HIVE_TOR_SOCKS_ORBOT}" ;;
  esac
}
socks_host() { printf '%s' "${1%%:*}"; }
socks_port() { printf '%s' "${1##*:}"; }
socks_ok()   { nc -z "$(socks_host "$1")" "$(socks_port "$1")" >/dev/null 2>&1; }

# parse separator
while [[ "${1:-}" != "--" && -n "${1:-}" ]]; do shift; done
[[ "${1:-}" == "--" ]] && shift || true
cmd="${*:-}"
[[ -n "$cmd" ]] || { echo "[proxy] empty command"; exit 64; }

socks="$(socks_of_mode)"
if ! socks_ok "$socks"; then
  echo "[proxy] SOCKS $socks not reachable"; exit 69
fi

export ALL_PROXY="socks5h://$socks"
if [[ "${WANT_TORSOCKS:-0}" -eq 1 ]] && command -v torsocks >/dev/null 2>&1; then
  exec torsocks -P "$(socks_host "$socks"):$(socks_port "$socks")" bash -lc "$cmd"
else
  exec bash -lc "$cmd"
fi
