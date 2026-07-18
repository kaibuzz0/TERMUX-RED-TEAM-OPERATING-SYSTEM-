#!/data/data/com.termux/files/usr/bin/bash
# Hive-Mind v4.0 Auto-Start Configuration
# Add this to ~/.bashrc for automatic Hive-Mind initialization

# Hive-Mind Environment
export HIVE_OS_ROOT="/root/hive-os"
export HIVE_SWARM_ROOT="/root/hive-swarm"
export HIVE_MIND_VERSION="4.0"

# Add to PATH
export PATH="${HIVE_OS_ROOT}/bin:$PATH"

# Check if we're in an interactive shell
if [[ $- == *i* ]]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  HIVE-MIND v${HIVE_MIND_VERSION}                               ║"
    echo "║  Hermes + Hive OS Integration                        ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    
    # Check for previous session
    LAST_SESSION="${HIVE_OS_ROOT}/run/last_session.json"
    if [ -f "$LAST_SESSION" ]; then
        LAST_TIME=$(cat "$LAST_SESSION" | python3 -c "import json,sys; print(json.load(sys.stdin).get('timestamp',0))" 2>/dev/null || echo "0")
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_TIME))
        
        if [ $DIFF -lt 3600 ]; then
            echo "🔁 Previous session: ${DIFF}s ago"
            echo "   Run 'hive-mind /recover' to restore context"
            echo ""
        fi
    fi
    
    # Start Hive OS services if not running
    if [ -f "${HIVE_OS_ROOT}/etc/startup.sh" ]; then
        echo "[*] Initializing Hive OS..."
        source "${HIVE_OS_ROOT}/etc/startup.sh" &>/dev/null
        echo ""
    fi
    
    # Show quick status
    echo "Quick commands:"
    echo "  hive-mind /status     - System status"
    echo "  hive-mind /help       - Full help"
    echo "  hive-mind             - Interactive mode"
    echo ""
    echo "Just type to talk to the AI, use / for OS commands"
    echo ""
fi

# Save session on exit
trap 'echo "{\"timestamp\": $(date +%s)}" > "${HIVE_OS_ROOT}/run/last_session.json" 2>/dev/null' EXIT
