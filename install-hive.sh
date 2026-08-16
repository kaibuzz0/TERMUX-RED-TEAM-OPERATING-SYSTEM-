#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_URL="${HIVE_BOOTSTRAP_URL:-}"
BOOTSTRAP_SHA256="${HIVE_BOOTSTRAP_SHA256:-}"
BUNDLE_URL="${HIVE_BUNDLE_URL:-}"
CHANNEL="${HIVE_CHANNEL:-parity-test}"
CURRENT_SEQUENCE="${HIVE_CURRENT_SEQUENCE:-0}"
DATA_ROOT="${HIVE_DATA_ROOT:-${HOME}/Hive-Ops/data}"
STATE_ROOT="${HIVE_STATE_ROOT:-${HOME}/Hive-Ops/state}"
APPROVE=1

usage() {
  cat <<'USAGE'
Hive OS V2 clean-Termux bootstrap

Usage:
  install-hive.sh --bootstrap-url HTTPS_URL --bootstrap-sha256 SHA256 \
                  --bundle-url HTTPS_URL [options]

Options:
  --bootstrap-url URL       HTTPS URL for hive-bootstrap.pyz
  --bootstrap-sha256 HEX    Expected SHA-256 of hive-bootstrap.pyz
  --bundle-url URL          HTTPS URL for the signed Hive release bundle
  --channel NAME            Informational selected channel (default: parity-test)
  --current-sequence N      Installed security sequence for anti-rollback (default: 0)
  --data-root PATH          Hive release data root
  --state-root PATH         Hive persistent state root
  --no-approve              Verify/stage only; do not activate
  -h, --help                Show this help

Environment variables with matching HIVE_* names may also be used.
The bootstrap never reads or modifies ~/.hermes or ~/.ssh.
USAGE
}

fail() {
  printf '[Hive OS] ERROR: %s\n' "$*" >&2
  exit 2
}

require_https() {
  case "$1" in
    https://*) ;;
    *) fail "$2 must use https://" ;;
  esac
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bootstrap-url) [ "$#" -ge 2 ] || fail "--bootstrap-url requires a value"; BOOTSTRAP_URL="$2"; shift 2 ;;
    --bootstrap-sha256) [ "$#" -ge 2 ] || fail "--bootstrap-sha256 requires a value"; BOOTSTRAP_SHA256="$2"; shift 2 ;;
    --bundle-url) [ "$#" -ge 2 ] || fail "--bundle-url requires a value"; BUNDLE_URL="$2"; shift 2 ;;
    --channel) [ "$#" -ge 2 ] || fail "--channel requires a value"; CHANNEL="$2"; shift 2 ;;
    --current-sequence) [ "$#" -ge 2 ] || fail "--current-sequence requires a value"; CURRENT_SEQUENCE="$2"; shift 2 ;;
    --data-root) [ "$#" -ge 2 ] || fail "--data-root requires a value"; DATA_ROOT="$2"; shift 2 ;;
    --state-root) [ "$#" -ge 2 ] || fail "--state-root requires a value"; STATE_ROOT="$2"; shift 2 ;;
    --no-approve) APPROVE=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[ -n "$BOOTSTRAP_URL" ] || fail "missing --bootstrap-url"
[ -n "$BOOTSTRAP_SHA256" ] || fail "missing --bootstrap-sha256"
[ -n "$BUNDLE_URL" ] || fail "missing --bundle-url"

require_https "$BOOTSTRAP_URL" "bootstrap URL"
require_https "$BUNDLE_URL" "bundle URL"

case "$BOOTSTRAP_SHA256" in
  *[!0-9a-fA-F]*|'') fail "bootstrap SHA-256 must be hexadecimal" ;;
esac
[ "${#BOOTSTRAP_SHA256}" -eq 64 ] || fail "bootstrap SHA-256 must be exactly 64 hex characters"
case "$CURRENT_SEQUENCE" in
  *[!0-9]*|'') fail "current security sequence must be a non-negative integer" ;;
esac

command -v pkg >/dev/null 2>&1 || fail "this bootstrap requires Termux (pkg not found)"

ensure_pkg() {
  local package="$1"
  if ! dpkg -s "$package" >/dev/null 2>&1; then
    printf '[Hive OS] Installing required Termux package: %s\n' "$package"
    pkg install -y "$package"
  fi
}

printf '[Hive OS] Preparing minimal bootstrap runtime...\n'
pkg update -y
ensure_pkg python
ensure_pkg python-cryptography
ensure_pkg curl

work_dir="$(mktemp -d "${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}/hive-bootstrap.XXXXXX")"
cleanup() { rm -rf "$work_dir"; }
trap cleanup EXIT HUP INT TERM
chmod 700 "$work_dir"
bootstrap_path="$work_dir/hive-bootstrap.pyz"

printf '[Hive OS] Downloading verified bootstrap runner...\n'
curl -fL --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 20 \
  -o "$bootstrap_path" "$BOOTSTRAP_URL"

actual_sha256="$(python - "$bootstrap_path" <<'PY'
import hashlib
import sys
from pathlib import Path
p = Path(sys.argv[1])
h = hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda: f.read(65536), b''):
        h.update(chunk)
print(h.hexdigest())
PY
)"

if [ "${actual_sha256,,}" != "${BOOTSTRAP_SHA256,,}" ]; then
  fail "bootstrap SHA-256 mismatch"
fi

printf '[Hive OS] Bootstrap integrity verified. Channel: %s\n' "$CHANNEL"
cmd=(
  python "$bootstrap_path"
  --bundle-url "$BUNDLE_URL"
  --platform termux
  --architecture "$(uname -m)"
  --current-sequence "$CURRENT_SEQUENCE"
  --data-root "$DATA_ROOT"
  --state-root "$STATE_ROOT"
  --prefix "${PREFIX:-/data/data/com.termux/files/usr}"
)
if [ "$APPROVE" -eq 1 ]; then
  cmd+=(--approve)
fi

"${cmd[@]}"

printf '\n[Hive OS] Bootstrap completed.\n'
if [ "$APPROVE" -eq 1 ]; then
  printf '[Hive OS] Run: hive version\n'
  printf '[Hive OS] Open a new Termux session to validate autoboot.\n'
else
  printf '[Hive OS] Release verified/staged only; activation was not approved.\n'
fi
