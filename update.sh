#!/data/data/com.termux/files/usr/bin/bash
# HIVE OS — Update from GitHub
# Pulls latest code, preserves credentials and config, restarts services.
# Usage: bash update.sh [--force]

set -euo pipefail
umask 077

REPO_URL="https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git"
INSTALL_DIR="$HOME/Hive-Ops"
BACKUP_DIR="$HOME/.hive_backup/$(date +%Y%m%d_%H%M%S)"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[1;36m'
RST='\033[0m'

log()  { echo -e "${GRN}[UPD]${RST} $1"; }
warn() { echo -e "${YLW}[WARN]${RST} $1"; }
err()  { echo -e "${RED}[ERR]${RST} $1"; exit 1; }
info() { echo -e "${CYN}[INFO]${RST} $1"; }

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

echo -e "${CYN}"
cat <<'EOF'
    ╔═══════════════════════════════════════════════════════╗
    ║        🔄 HIVE OS UPDATE SERVICE                     ║
    ╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${RST}"

# ── Check existing install ───────────────────────────────
if [ ! -d "$INSTALL_DIR/.git" ]; then
    err "Hive OS not found at $INSTALL_DIR. Run install-termux.sh first."
fi

# ── Backup credentials ───────────────────────────────────
log "Backing up credentials..."
mkdir -p "$BACKUP_DIR"
if [ -d "$HOME/.hive_auth" ]; then
    cp -r "$HOME/.hive_auth" "$BACKUP_DIR/"
    log "Auth backup: $BACKUP_DIR/.hive_auth"
fi

# ── Backup custom config ─────────────────────────────────
if [ -f "$HOME/.hive_ops.txt" ]; then
    cp "$HOME/.hive_ops.txt" "$BACKUP_DIR/"
fi
if [ -f "$HOME/.bashrc" ]; then
    cp "$HOME/.bashrc" "$BACKUP_DIR/"
fi

# ── Fetch updates ────────────────────────────────────────
log "Fetching latest from GitHub..."
cd "$INSTALL_DIR"

if [ "$FORCE" -eq 1 ]; then
    warn "Force mode: stashing local changes..."
    git stash || true
fi

git fetch origin master || err "Failed to fetch from GitHub"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Already up to date. Nothing to do."
    exit 0
fi

log "Update available: $LOCAL → $REMOTE"
info "Changes:"
git log --oneline "$LOCAL..$REMOTE" | head -10

git pull origin master || err "git pull failed"
log "Code updated ✓"

# ── Restore credentials ────────────────────────────────────
log "Restoring credentials..."
if [ -d "$BACKUP_DIR/.hive_auth" ]; then
    cp -r "$BACKUP_DIR/.hive_auth" "$HOME/"
    chmod 700 "$HOME/.hive_auth"
    chmod 600 "$HOME/.hive_auth/passwd" 2>/dev/null || true
    log "Credentials restored ✓"
fi

# ── Re-link binaries ─────────────────────────────────────
log "Re-linking binaries..."
mkdir -p "$HOME/bin"
for bin in "$INSTALL_DIR/Hive Ops Final/bin"/hive*; do
    [ -f "$bin" ] || continue
    name=$(basename "$bin")
    ln -sf "$bin" "$HOME/bin/$name" 2>/dev/null || true
done
log "Binaries linked ✓"

# ── Update boot script ───────────────────────────────────
BOOT_DIR="$HOME/.termux/boot"
if [ -f "$INSTALL_DIR/Hive Ops Final/.termux/boot/00-hive-secure.sh" ]; then
    mkdir -p "$BOOT_DIR"
    cp "$INSTALL_DIR/Hive Ops Final/.termux/boot/00-hive-secure.sh" "$BOOT_DIR/"
    chmod +x "$BOOT_DIR/00-hive-secure.sh"
    log "Boot script updated ✓"
fi

# ── Finish ─────────────────────────────────────────────────
echo ""
echo -e "${GRN}╔═══════════════════════════════════════════════════════╗${RST}"
echo -e "${GRN}║${RST}  ✅ Hive OS Updated Successfully!                  ${GRN}║${RST}"
echo -e "${GRN}╚═══════════════════════════════════════════════════════╝${RST}"
echo ""
echo -e "  ${CYN}Backup:${RST} $BACKUP_DIR"
echo -e "  ${CYN}Restart:${RST} source ~/.bashrc  OR  exit & reopen Termux"
echo ""
