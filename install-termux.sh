#!/data/data/com.termux/files/usr/bin/bash
# HIVE OS — Termux One-Line Installer v2.0
# Usage: curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/master/install-termux.sh | bash
#    OR: bash install-termux.sh
#
# Installs: Hive OS + Secure Login + Enhanced UI + Termux:Boot support

set -euo pipefail
umask 077

REPO_URL="https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git"
INSTALL_DIR="$HOME/Hive-Ops"
LOG_FILE="$HOME/hive_install.log"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[1;36m'
WHT='\033[1;37m'
DIM='\033[2m'
RST='\033[0m'

log()   { echo -e "${GRN}[HIVE]${RST} $1" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YLW}[WARN]${RST} $1" | tee -a "$LOG_FILE"; }
err()   { echo -e "${RED}[ERR] ${RST} $1" | tee -a "$LOG_FILE"; exit 1; }
info()  { echo -e "${CYN}[INFO]${RST} $1" | tee -a "$LOG_FILE"; }

banner() {
    clear 2>/dev/null || true
    echo -e "${CYN}"
    cat <<'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██╗  ██╗██╗██╗   ██╗███████╗     ██████╗ ███████╗          ║
    ║   ██║  ██║██║██║   ██║██╔════╝    ██╔═══██╗██╔════╝          ║
    ║   ███████║██║██║   ██║█████╗      ██║   ██║███████╗          ║
    ║   ██╔══██║██║╚██╗ ██╔╝██╔══╝      ██║   ██║╚════██║          ║
    ║   ██║  ██║██║ ╚████╔╝ ███████╗    ╚██████╔╝███████║          ║
    ║   ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝     ╚═════╝ ╚══════╝          ║
    ║                                                               ║
    ║              🐍 AI↔AI Security System 🐍                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${RST}"
    echo -e "    ${DIM}Installer v2.0 | Termux Edition | Secure Login + Enhanced UI${RST}"
    echo ""
}

# ── Check Termux ───────────────────────────────────────────
check_termux() {
    log "Checking environment..."
    if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux" ]; then
        err "This script is for Termux only. Install Termux from F-Droid."
    fi
    if ! command -v pkg >/dev/null 2>&1; then
        err "pkg command not found. Not a valid Termux environment."
    fi
    log "Termux confirmed ✓"
}

# ── Install Dependencies ─────────────────────────────────
install_deps() {
    log "Installing dependencies..."
    pkg update -y || warn "Package update had issues, continuing..."
    
    PACKAGES="git python python-pip curl wget nano vim tmux openssh openssl-tool termux-api tor torsocks net-tools procps psmisc lsof jq clang make cmake ncurses-utils"
    
    for pkg in $PACKAGES; do
        if ! command -v "$pkg" >/dev/null 2>&1 && [ "$pkg" != "termux-api" ]; then
            info "Installing $pkg..."
            pkg install -y "$pkg" 2>&1 || warn "Could not install $pkg"
        fi
    done
    
    log "Dependencies ready ✓"
}

# ── Clone / Update Repo ────────────────────────────────────
get_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log "Existing install found. Updating..."
        cd "$INSTALL_DIR"
        git pull --depth 1 origin master || warn "git pull failed, keeping local copy"
    else
        log "Cloning Hive OS repository..."
        rm -rf "$INSTALL_DIR"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
    log "Repository ready ✓"
}

# ── Install Components ─────────────────────────────────────
install_components() {
    log "Installing components..."
    
    # Symlink binaries
    mkdir -p "$HOME/bin"
    for bin in "$INSTALL_DIR/Hive Ops Final/bin"/hive*; do
        [ -f "$bin" ] || continue
        name=$(basename "$bin")
        ln -sf "$bin" "$HOME/bin/$name" 2>/dev/null || true
    done
    
    # Add to PATH if needed
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/bin:$PATH"
    fi
    
    # Bash integration
    BASHRC="$HOME/.bashrc"
    if ! grep -q "hive_ops_banner" "$BASHRC" 2>/dev/null; then
        echo "" >> "$BASHRC"
        echo "# Hive Ops Integration" >> "$BASHRC"
        echo 'source "$HOME/Hive-Ops/Hive Ops Final/etc/bash-integration.sh" 2>/dev/null || true' >> "$BASHRC"
        log "Bash integration added ✓"
    fi
    
    log "Components installed ✓"
}

# ── Secure Login Setup ─────────────────────────────────────
setup_secure_login() {
    log "Setting up secure login..."
    
    # Copy secure boot to Termux:Boot
    BOOT_DIR="$HOME/.termux/boot"
    mkdir -p "$BOOT_DIR"
    
    cp "$INSTALL_DIR/Hive Ops Final/.termux/boot/00-hive-secure.sh" "$BOOT_DIR/00-hive-secure.sh"
    chmod +x "$BOOT_DIR/00-hive-secure.sh"
    
    log "Secure boot copied to ~/.termux/boot/ ✓"
    info "Install Termux:Boot app from F-Droid for auto-start."
}

# ── First-Time Credentials ─────────────────────────────────
setup_credentials() {
    AUTH_DIR="$HOME/.hive_auth"
    if [ ! -f "$AUTH_DIR/passwd" ]; then
        log "First-time setup: creating credentials..."
        mkdir -p "$AUTH_DIR"
        chmod 700 "$AUTH_DIR"
        
        echo ""
        echo -e "${YLW}🔐 Create your Hive login credentials:${RST}"
        echo ""
        
        while true; do
            printf "${CYN}Password (min 4 chars):${RST} "
            read -rs PASS1
            printf "\n"
            printf "${CYN}Confirm:${RST} "
            read -rs PASS2
            printf "\n"
            
            [ "$PASS1" = "$PASS2" ] || { warn "Passwords don't match, try again"; continue; }
            [ ${#PASS1} -ge 4 ] || { warn "Too short, try again"; continue; }
            break
        done
        
        while true; do
            printf "${CYN}4-digit PIN:${RST} "
            read -rs PIN1
            printf "\n"
            printf "${CYN}Confirm PIN:${RST} "
            read -rs PIN2
            printf "\n"
            
            [ "$PIN1" = "$PIN2" ] || { warn "PINs don't match, try again"; continue; }
            [[ "$PIN1" =~ ^[0-9]{4}$ ]] || { warn "Must be exactly 4 digits"; continue; }
            break
        done
        
        printf '%s\n%s' "$PASS1" "$PIN1" | base64 > "$AUTH_DIR/passwd"
        chmod 600 "$AUTH_DIR/passwd"
        
        log "Credentials saved ✓"
    else
        log "Existing credentials found, skipping setup"
    fi
}

# ── Finish ─────────────────────────────────────────────────
finish() {
    echo ""
    echo -e "${GRN}╔═══════════════════════════════════════════════════════════════╗${RST}"
    echo -e "${GRN}║${RST}  ${WHT}🎉 Hive OS Installation Complete!${RST}                          ${GRN}║${RST}"
    echo -e "${GRN}╚═══════════════════════════════════════════════════════════════╝${RST}"
    echo ""
    echo -e "  ${CYN}Quick Commands:${RST}"
    echo -e "    ${WHT}hive-ui-v2${RST}        Launch enhanced TUI"
    echo -e "    ${WHT}hive status${RST}       System status"
    echo -e "    ${WHT}hive health${RST}       Health check"
    echo -e "    ${WHT}hive dashboard${RST}    Legacy dashboard"
    echo -e "    ${WHT}hive-secure-login${RST} Run secure login manually"
    echo ""
    echo -e "  ${CYN}Auto-Launch:${RST}"
    echo -e "    Install Termux:Boot app → Hive starts on device boot"
    echo -e "    Login required every time (password + PIN)"
    echo ""
    echo -e "  ${CYN}Aliases added:${RST}"
    echo -e "    ${WHT}hh${RST} = hive health | ${WHT}hs${RST} = hive status | ${WHT}hui${RST} = hive-ui-v2"
    echo -e "    ${WHT}hsec${RST} = hive-secure-login"
    echo ""
    echo -e "  ${YLW}Restart Termux or run: source ~/.bashrc${RST}"
    echo ""
}

# ── Main ─────────────────────────────────────────────────
main() {
    banner
    check_termux
    install_deps
    get_repo
    install_components
    setup_secure_login
    setup_credentials
    finish
}

main "$@"
