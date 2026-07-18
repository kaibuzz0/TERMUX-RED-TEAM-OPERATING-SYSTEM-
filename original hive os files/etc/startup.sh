#!/data/data/com.termux/files/usr/bin/bash
# Hive OS Startup Script
# Run automatically on Termux session start

HIVE_OS_ROOT="/root/hive-os"
HIVE_SWARM_ROOT="/root/hive-swarm"

export PATH="${HIVE_OS_ROOT}/bin:$PATH"
export HIVE_OS_ROOT
export HIVE_SWARM_ROOT

# Create necessary directories
mkdir -p ${HIVE_OS_ROOT}/{run,log,cache,etc}
mkdir -p ${HIVE_OS_ROOT}/run/{pids,sockets}

# Start autostart services
echo "[*] Starting Hive OS services..."
python3 ${HIVE_OS_ROOT}/bin/hive-service start-all

# Show status
echo ""
echo "[*] Hive OS Status:"
python3 ${HIVE_OS_ROOT}/bin/hive-os status 2>/dev/null || echo "  Run 'hive-os status' for details"

echo ""
echo "[*] Hive OS v3.1-OS-INTEGRATED ready"
echo "    Commands: hive-os, hive-service, hive-hardware, hive-dashboard"
echo ""
