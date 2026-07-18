#!/data/data/com.termux/files/usr/bin/bash
# Hive OS Installer
# Restores the complete Hive network/stealth system from GitHub

set -Eeuo pipefail

HIVE_REPO="${1:-$(pwd)}"
HIVE_HOME="${HIVE_HOME:-$HOME/hive}"
HIVE_CONFIG="${HOME}/.config/hive"
BOOT_DIR="${HOME}/.termux/boot"

echo "=== HIVE OS INSTALLER ==="
echo "Repo: $HIVE_REPO"
echo "Target: $HIVE_HOME"
echo ""

# Check dependencies
echo "[*] Checking dependencies..."
for cmd in git tmux nc tor curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[!] Missing: $cmd - install with: pkg install $cmd"
        exit 1
    fi
done
echo "[✓] All dependencies present"

# Create directories
echo "[*] Creating directories..."
mkdir -p "$HIVE_HOME"/{bin,etc/tor,etc/services,logs,state/tor}
mkdir -p "$HIVE_CONFIG"
mkdir -p "$BOOT_DIR"

# Copy OS files
echo "[*] Installing Hive OS binaries..."
cp "$HIVE_REPO/hive-os/bin/"*.sh "$HIVE_HOME/bin/"
cp "$HIVE_REPO/hive-os/bin/hive" "$HIVE_HOME/bin/"
chmod +x "$HIVE_HOME/bin/"*

# Copy configs
echo "[*] Installing configuration..."
cp "$HIVE_REPO/hive-os/etc/tor/torrc" "$HIVE_HOME/etc/tor/"
cp "$HIVE_REPO/hive-os/etc/escape.txt" "$HIVE_HOME/etc/"
cp "$HIVE_REPO/hive-os/etc/dev.aliases.sh" "$HIVE_HOME/etc/"
cp "$HIVE_REPO/hive-os/etc/services/"*.svc "$HIVE_HOME/etc/services/" 2>/dev/null || true

# Copy environment
echo "[*] Installing environment..."
cp "$HIVE_REPO/.config/hive/env.sh" "$HIVE_CONFIG/"

# Copy boot script
echo "[*] Installing boot script..."
cp "$HIVE_REPO/.termux/boot/00-hive.sh" "$BOOT_DIR/"
chmod +x "$BOOT_DIR/00-hive.sh"

# Create state files
touch "$HIVE_HOME/state/net.mode"
echo "orbot" > "$HIVE_HOME/state/net.mode"

# Set permissions
chmod 700 "$HIVE_HOME"
chmod 600 "$HIVE_HOME/etc/tor/torrc" 2>/dev/null || true

echo ""
echo "=== INSTALLATION COMPLETE ==="
echo ""
echo "Next steps:"
echo "  1. Source environment: source ~/.config/hive/env.sh"
echo "  2. Start Hive:        hive start"
echo "  3. Check status:      hive status"
echo "  4. Run health check:  hive health"
echo ""
echo "Boot script installed at: $BOOT_DIR/00-hive.sh"
echo "Hive will auto-start on device boot."
echo ""
echo "Commands:"
echo "  hive {start|stop|status|health|logs|ps}"
echo "  hive net {orbot|local|off|newnym|status|test}"
echo "  hive services {list|start|stop|status|health|ensure}"
