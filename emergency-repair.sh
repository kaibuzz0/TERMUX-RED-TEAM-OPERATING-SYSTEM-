#!/data/data/com.termux/files/usr/bin/bash
# HIVE OS — Emergency Repair
# Nuclear option: wipes and re-installs from GitHub, preserving credentials.
# Usage: bash emergency-repair.sh [--full-nuke]
#
# Without --full-nuke: preserves ~/.hive_auth, ~/.bashrc customizations
# With --full-nuke: complete wipe (you will lose your login credentials!)

set -uo pipefail
umask 077

REPO_URL="https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git"
INSTALL_DIR="$HOME/Hive-Ops"
RESCUE_DIR="$HOME/.hive_rescue"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[1;36m'
WHT='\033[1;37m'
RST='\033[0m'

log()  { echo -e "${GRN}[RSC]${RST} $1"; }
warn() { echo -e "${YLW}[WARN]${RST} $1"; }
err()  { echo -e "${RED}[ERR]${RST} $1"; }
info() { echo -e "${CYN}[INFO]${RST} $1"; }
ask()  {
    printf "${YLW}$1 [y/N]: ${RST}"
    read -r REPLY
    [[ "$REPLY" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }
}

NUKE=0
[[ "${1:-}" == "--full-nuke" ]] && NUKE=1

clear 2>/dev/null || true
echo -e "${RED}"
cat <<'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ⚠️  HIVE OS EMERGENCY REPAIR SERVICE                       ║
    ║                                                               ║
    ║   This will re-download and re-install Hive OS from GitHub   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${RST}"

if [ "$NUKE" -eq 1 ]; then
    warn "FULL NUKE MODE ENABLED"
    err "This will DELETE everything including your login credentials!"
    ask "Are you absolutely sure you want to ERASE all Hive data?"
else
    ask "Repair Hive OS? Your credentials will be preserved."
fi

# ── Preserve ───────────────────────────────────────────────
mkdir -p "$RESCUE_DIR"

if [ "$NUKE" -eq 0 ]; then
    log "Preserving credentials..."
    if [ -d "$HOME/.hive_auth" ]; then
        cp -r "$HOME/.hive_auth" "$RESCUE_DIR/"
        log "  → Auth saved"
    fi
    if [ -f "$HOME/.hive_ops.txt" ]; then
        cp "$HOME/.hive_ops.txt" "$RESCUE_DIR/"
        log "  → Notes saved"
    fi
fi

log "Preserving .bashrc backup..."
cp "$HOME/.bashrc" "$RESCUE_DIR/bashrc.backup" 2>/dev/null || true

# ── Wipe ───────────────────────────────────────────────────
log "Removing old installation..."
rm -rf "$INSTALL_DIR"
rm -rf "$HOME/bin/hive"*
rm -f "$HOME/.termux/boot/00-hive*"

if [ "$NUKE" -eq 1 ]; then
    rm -rf "$HOME/.hive_auth"
    rm -f "$HOME/.hive_ops.txt"
    warn "Credentials deleted (nuke mode)"
fi

# ── Re-clone ───────────────────────────────────────────────
log "Downloading fresh copy from GitHub..."
git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" || err "git clone failed. Check network."
log "Download complete ✓"

# ── Restore ────────────────────────────────────────────────
if [ "$NUKE" -eq 0 ] && [ -d "$RESCUE_DIR/.hive_auth" ]; then
    log "Restoring credentials..."
    cp -r "$RESCUE_DIR/.hive_auth" "$HOME/"
    chmod 700 "$HOME/.hive_auth"
    chmod 600 "$HOME/.hive_auth/passwd" 2>/dev/null || true
fi

if [ -f "$RESCUE_DIR/.hive_ops.txt" ]; then
    cp "$RESCUE_DIR/.hive_ops.txt" "$HOME/"
fi

# ── Re-install ───────────────────────────────────────────
log "Re-installing components..."

# Symlink binaries
mkdir -p "$HOME/bin"
for bin in "$INSTALL_DIR/Hive Ops Final/bin"/hive*; do
    [ -f "$bin" ] || continue
    name=$(basename "$bin")
    ln -sf "$bin" "$HOME/bin/$name" 2>/dev/null || true
done

# Re-add bash integration if missing
if ! grep -q "hive_ops_banner" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# Hive Ops Integration" >> "$HOME/.bashrc"
    echo 'source "$HOME/Hive-Ops/Hive Ops Final/etc/bash-integration.sh" 2>/dev/null || true' >> "$HOME/.bashrc"
fi

# Re-copy boot script
BOOT_DIR="$HOME/.termux/boot"
if [ -f "$INSTALL_DIR/Hive Ops Final/.termux/boot/00-hive-secure.sh" ]; then
    mkdir -p "$BOOT_DIR"
    cp "$INSTALL_DIR/Hive Ops Final/.termux/boot/00-hive-secure.sh" "$BOOT_DIR/"
    chmod +x "$BOOT_DIR/00-hive-secure.sh"
    log "Boot script restored ✓"
fi

# ── If nuked, force credential re-setup ──────────────────
if [ "$NUKE" -eq 1 ]; then
    warn "You must create new credentials (nuke mode)."
    mkdir -p "$HOME/.hive_auth"
    
    echo ""
    printf "${CYN}New password (min 4 chars):${RST} "
    read -rs P1; printf "\n"
    printf "${CYN}Confirm:${RST} "
    read -rs P2; printf "\n"
    
    if [ "$P1" != "$P2" ] || [ ${#P1} -lt 4 ]; then
        err "Password setup failed. Run manually later."
    fi
    
    printf "${CYN}4-digit PIN:${RST} "
    read -rs PIN1; printf "\n"
    printf "${CYN}Confirm PIN:${RST} "
    read -rs PIN2; printf "\n"
    
    if [ "$PIN1" != "$PIN2" ] || ! [[ "$PIN1" =~ ^[0-9]{4}$ ]]; then
        err "PIN setup failed. Run manually later."
    fi
    
    printf '%s\n%s' "$P1" "$PIN1" | base64 > "$HOME/.hive_auth/passwd"
    chmod 600 "$HOME/.hive_auth/passwd"
    log "New credentials created ✓"
fi

# ── Finish ───────────────────────────────────────────────
echo ""
echo -e "${GRN}╔═══════════════════════════════════════════════════════════════╗${RST}"
echo -e "${GRN}║${RST}  ✅ EMERGENCY REPAIR COMPLETE                              ${GRN}║${RST}"
echo -e "${GRN}╚═══════════════════════════════════════════════════════════════╝${RST}"
echo ""
echo -e "  ${CYN}What was done:${RST}"
echo -e "    • Old installation removed"
echo -e "    • Fresh code downloaded from GitHub"
echo -e "    • Credentials ${NUKE:+recreated}${NUKE:-preserved}"
echo -e "    • Binaries re-linked"
echo -e "    • Boot script restored"
echo ""
echo -e "  ${CYN}Next steps:${RST}"
echo -e "    1. source ~/.bashrc  OR  exit & reopen Termux"
echo -e "    2. Type ${WHT}hive-ui-v2${RST} to launch the enhanced UI"
echo -e "    3. Or just close and reopen — auto-login will trigger"
echo ""

if [ "$NUKE" -eq 0 ]; then
    echo -e "  ${GRN}Rescue files kept at:${RST} $RESCUE_DIR"
fi
