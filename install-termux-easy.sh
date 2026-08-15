#!/data/data/com.termux/files/usr/bin/env bash
# Hive OS Termux easy-start wrapper.
# This script only delegates to existing, already-supported commands.
# It does not install packages, modify .bashrc, or start services.

set -euo pipefail

REPO_URL="https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git"
INSTALL_DIR="\${HOME}/Hive-Ops"
TAG="hive-os-v1.0.0"

echo "[Hive OS] Cloning stable release tag ${TAG}..."
if [ -d "${INSTALL_DIR}/.git" ]; then
    cd "${INSTALL_DIR}"
    git fetch --depth 1 origin "${TAG}"
    git checkout "${TAG}"
else
    git clone --depth 1 --branch "${TAG}" "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

echo "[Hive OS] Installing Python dependencies..."
if ! python -m pip install -r requirements.txt; then
    echo "[Hive OS] ERROR: Failed to install requirements. Stopping." >&2
    exit 1
fi

echo "[Hive OS] Running quick checks..."
python bin/hive --help >/dev/null
python bin/hive config validate
python bin/hive broker capabilities

echo "[Hive OS] Ready. Inspect the safe installer plan with:"
echo "  cd ${INSTALL_DIR}"
echo "  python -m installer.install --check"
echo "  python -m installer.install --plan"
echo "  python -m installer.install --dry-run"
