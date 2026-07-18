#!/data/data/com.termux/files/usr/bin/bash
# HIVE OPS FINAL - Shell Integration with Banner
# Source this in .bashrc: source ~/Hive\ Ops\ Final/etc/bash-integration.sh

# Load unified environment
HIVE_FINAL="${HIVE_FINAL:-$HOME/Hive Ops Final}"
if [[ -r "$HIVE_FINAL/etc/env.sh" ]]; then
    source "$HIVE_FINAL/etc/env.sh"
fi

# Colors
HCYAN='\e[1;36m'
HGRN='\e[1;32m'
HYLW='\e[1;33m'
HPRP='\e[1;35m'
HRED='\e[1;31m'
RESET='\e[0m'

# Ensure notes file exists
[[ -f "$HOME/.hive_ops.txt" ]] || cat > "$HOME/.hive_ops.txt" <<'EOF'
🟢 nano ~/.bashrc 🟢 ai-snapshot --full            
🟢 health 🟢                                       
🟢 rm ~/bin/xxxxxx 🟢
EOF

# ===== Hive Ops Banner v5.0 =====
hive_ops_banner() {
    local top=0 left=0
    local box_w=56 box_h=13
    
    # Clear banner area
    tput sc
    for r in $(seq 0 $((box_h))); do
        tput cup $((top+r)) $left
        printf "%-${box_w}s" " "
    done
    
    # Draw outer box
    tput cup $top $left
    printf "┌"; printf '─%.0s' $(seq 1 $((box_w-2))); printf "┐"
    for r in $(seq 1 $((box_h-1))); do
        tput cup $((top+r)) $left; printf "│"
        tput cup $((top+r)) $((left+box_w-1)); printf "│"
    done
    tput cup $((top+box_h)) $left
    printf "└"; printf '─%.0s' $(seq 1 $((box_w-2))); printf "┘"
    
    # Title
    local title=" Hive Ops Final v5.0 🧠 ✓ ⚡ 🔧 "
    tput cup $top $((left+2))
    printf "${HCYAN}${title}${RESET}"
    
    # Profile avatar
    local ptop=$((top+2)) pleft=$((left+2))
    tput cup $ptop $pleft;       printf "┌────┐"
    tput cup $((ptop+1)) $pleft; printf "│(•_•)│"
    tput cup $((ptop+2)) $pleft; printf "│/| |\\│"
    tput cup $((ptop+3)) $pleft; printf "│ / \\ │"
    tput cup $((ptop+4)) $pleft; printf "└────┘"
    
    # Info
    local info_left=$((pleft+10))
    tput cup $((ptop+0)) $info_left; printf "${HGRN}Profile:${RESET} Hive Operator"
    tput cup $((ptop+1)) $info_left; printf "${HGRN}Mode:${RESET} ${HPRP}Active${RESET}"
    tput cup $((ptop+2)) $info_left; printf "${HGRN}Date:${RESET} $(date '+%Y-%m-%d %H:%M')"
    tput cup $((ptop+3)) $info_left; printf "${HGRN}Node:${RESET} $(uname -n)"
    
    # Status line
    local status_line=$(python3 "$HIVE_FINAL/lib/swarm_bridge.py" status 2>/dev/null | grep -o '"status": "[^"]*"' | cut -d'"' -f4 || echo "Ready")
    tput cup $((ptop+4)) $info_left; printf "${HYLW}Swarm:${RESET} ${status_line}"
    
    # Notes header
    local notes_top=$((top+8)) notes_left=$((left+2)) notes_w=$((box_w-4))
    tput cup $notes_top $notes_left
    printf "${HYLW}Quick Commands:${RESET}"
    tput cup $((notes_top+1)) $notes_left
    printf "─%.0s" $(seq 1 $((notes_w)))
    
    # Notes lines
    local i=0 line
    while IFS= read -r line && [ $i -lt 3 ]; do
        line="${line/#\# /}"
        tput cup $((notes_top+1+i+1)) $notes_left
        printf "%-${notes_w}.${notes_w}s" "$line"
        i=$((i+1))
    done < "$HOME/.hive_ops.txt"
    
    # Footer
    tput cup $((top+box_h-1)) $((left+2))
    printf "${HGRN}[${RESET} hive status ${HGRN}|${RESET} health ${HGRN}|${RESET} dashboard ${HGRN}]${RESET}"
    
    # Return cursor
    tput rc
    tput cup $((top+box_h+2)) 0
}

# Draw on interactive shells
case $- in
    *i*) 
        # Only if terminal supports tput
        if command -v tput &>/dev/null && [[ -t 1 ]]; then
            hive_ops_banner 2>/dev/null || true
        fi
        ;;
esac

# Quick aliases
alias hh='hive health'
alias hs='hive status'
alias hd='hive dashboard'
alias hn='hive net status'
alias hsv='hive services status'
alias hlog='hive logs'
alias hps='hive ps'
