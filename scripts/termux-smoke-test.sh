#!/usr/bin/env bash
# Termux smoke-test helper for HIVE OS FINAL PRODUCTION.
# Usage: ./scripts/termux-smoke-test.sh [--dry-run|--check]

set -euo pipefail

DRY_RUN=0
CHECK=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --check) CHECK=1 ;;
  esac
done

if [ "$CHECK" -eq 1 ]; then
  bash -n "$(dirname "$0")/../install-termux-easy.sh"
  echo "Syntax OK"
  exit 0
fi

TERMUX_PREFIX="${TERMUX_PREFIX:-/data/data/com.termux/files/usr}"
HIVE_HOME="${HOME}/.hive"

echo "Termux prefix: $TERMUX_PREFIX"
echo "Hive home: $HIVE_HOME"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry-run: would create $HIVE_HOME and stage runtime under $TERMUX_PREFIX/opt/hive"
  exit 0
fi

# Real install path is intentionally operator-gated; the CI simulation does not run this.
"$(dirname "$0")/../install-termux-easy.sh"
