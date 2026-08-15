#!/data/data/com.termux/files/usr/bin/env bash
# Hive OS Termux easy-start wrapper (1.0.1 repair / CURRENT MASTER).
# This script only delegates to existing, already-supported commands.
# It does not install packages, modify .bashrc, or start services.
#
# NOTE: This installs the CURRENT MASTER branch (1.0.1 repair) until
# hive-os-v1.0.1 is formally tagged.

set -euo pipefail

REPO_URL="https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git"
INSTALL_DIR="${HOME}/Hive-Ops"

echo "[Hive OS] Cloning CURRENT MASTER (1.0.1 repair)..."
if [ -d "${INSTALL_DIR}/.git" ]; then
    cd "${INSTALL_DIR}"
    git fetch --depth 1 origin master
    git reset --hard origin/master
else
    git clone --depth 1 --branch master "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

echo "[Hive OS] Installing Termux system packages if needed..."
for pkg in python python-cryptography; do
    if ! dpkg -l "${pkg}" >/dev/null 2>&1; then
        echo "[Hive OS]   pkg install -y ${pkg}"
        pkg install -y "${pkg}" || true
    fi
done

echo "[Hive OS] Installing core runtime Python dependencies..."
if ! python -m pip install -r requirements-runtime.txt; then
    echo "[Hive OS] ERROR: Failed to install core runtime requirements. Stopping." >&2
    exit 1
fi

echo "[Hive OS] Running core command checks..."
python bin/hive --help >/dev/null
python bin/hive --runtime-info --json >/dev/null
python bin/hive config validate
python bin/hive policy status
python bin/hive broker capabilities
python bin/hive ops --json >/dev/null

echo "[Hive OS] Ready. Inspect the safe installer plan with:"
echo "  cd ${INSTALL_DIR}"
echo "  python -m installer.install --check"
echo "  python -m installer.install --plan"
echo "  python -m installer.install --dry-run"
echo ""
echo "[Hive OS] Optional extras (legacy AI/network tools) available via:"
echo "  python -m pip install -r requirements-extras.txt"
