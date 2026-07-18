#!/data/data/com.termux/files/usr/bin/bash
# HIVE OPS FINAL - Termux Boot Script
# Auto-starts Hive on device boot

set -Eeuo pipefail
umask 077

# Source unified environment
ENV_FILE="$HOME/Hive Ops Final/etc/env.sh"
if [[ -r "$ENV_FILE" ]]; then
    source "$ENV_FILE"
else
    # Fallback paths
    export HIVE_HOME="${HIVE_HOME:-$HOME/hive}"
    export HIVE_BIN="$HIVE_HOME/bin"
    export PATH="$HIVE_BIN:$PATH"
fi

# Check if boot enabled
: "${HIVE_BOOT_ENABLE:=1}"
if [[ "$HIVE_BOOT_ENABLE" != "1" ]]; then
    echo "[boot] Hive boot disabled"
    exit 0
fi

# Check if already running
if tmux has-session -t hive 2>/dev/null; then
    echo "[boot] Hive already running"
    exit 0
fi

# Start Hive using unified command
if [[ -f "$HOME/Hive Ops Final/bin/hive" ]]; then
    echo "[boot] Starting Hive Ops Final..."
    python3 "$HOME/Hive Ops Final/bin/hive" start
else
    # Fallback to legacy
    echo "[boot] Starting Hive (legacy)..."
    "$HIVE_BIN/hive" start 2>/dev/null || true
fi

# Optional: Show banner
if [[ -f "$HOME/.hive_ops.txt" ]]; then
    echo ""
    head -3 "$HOME/.hive_ops.txt" 2>/dev/null || true
fi

echo "[boot] Hive started"
