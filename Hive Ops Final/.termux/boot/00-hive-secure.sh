#!/data/data/com.termux/files/usr/bin/bash
# TERMUX BOOT — Secure Hive Launcher
# Place in ~/.termux/boot/ with Termux:Boot app
# 
# This script:
#   1. Checks if secure login exists
#   2. Falls back to old boot if not installed
#   3. Cleans up on exit

set -euo pipefail
umask 077

HIVE_FINAL="${HIVE_FINAL:-$HOME/Hive Ops Final}"
SECURE_LOGIN="$HIVE_FINAL/bin/hive-secure-login"

# ── Check if secure login installed ────────────────────────
if [ -f "$SECURE_LOGIN" ]; then
    # Secure login exists — use it
    exec bash "$SECURE_LOGIN"
else
    # Fallback to old boot (legacy mode)
    echo "[boot] Secure login not found, using legacy boot..."
    
    ENV_FILE="$HIVE_FINAL/etc/env.sh"
    if [[ -r "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    export HIVE_HOME="${HIVE_HOME:-$HOME/hive}"
    export HIVE_BIN="$HIVE_HOME/bin"
    export PATH="$HIVE_BIN:$PATH"
    
    if [ -f "$HOME/.hive_ops.txt" ]; then
        head -3 "$HOME/.hive_ops.txt" 2>/dev/null || true
    fi
    
    # Start Hive
    if [ -f "$HIVE_FINAL/bin/hive" ]; then
        python3 "$HIVE_FINAL/bin/hive" start 2>/dev/null &
    fi
fi
