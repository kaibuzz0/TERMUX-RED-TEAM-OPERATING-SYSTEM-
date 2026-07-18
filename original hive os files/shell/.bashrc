#!/data/data/com.termux/files/usr/bin/bash

# Load Hive env
[ -f "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"

# >>> hive env >>>
[ -r "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"
# <<< hive env <<<

export PATH="$HOME/bin:$PATH"
alias health="health"         # pretty mode
alias health:json="health --json"
alias health:brief="health --brief"


# ===== Hive Ops Banner (Termux) =====
# Draws a small profile square in the upper-left and a "Hive Ops" box with an editable notes area.
# Edit your notes here: ~/.hive_ops.txt

# Colors (tweak if you like)
HCYAN='\e[1;36m' HGRN='\e[1;32m' HYLW='\e[1;33m' HPRP='\e[1;35m' HRED='\e[1;31m' RESET='\e[0m'

# Ensure notes file exists
[ -f "$HOME/.hive_ops.txt" ] || cat > "$HOME/.hive_ops.txt" <<'EOF'
# Hive Ops Notes (edit me)
# Example commands or reminders:
# - srv start mini-ai
# - hive status
# - update && upgrade
EOF

hive_ops_banner() {
  # Box geometry
  local top=0 left=0
  local box_w=54  # overall width of the Hive Ops box
  local box_h=12  # overall height
  local notes_rows=6  # how many lines of notes to show

  # Move to top-left and clear just the banner area (so it stays tidy)
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

  # Title bar
  local title=" Hive Ops box + ai + coms + torfox "
  tput cup $top $((left+2))
  printf "${HCYAN}${title}${RESET}"

  # Small profile square (upper-left inside the box)
  # Position relative to the box
  local ptop=$((top+2)) pleft=$((left+2))
  tput cup $ptop $pleft;       printf "┌────┐"
  tput cup $((ptop+1)) $pleft; printf "│(•_•)│"
  tput cup $((ptop+2)) $pleft; printf "│/| |\\│"
  tput cup $((ptop+3)) $pleft; printf "│ / \\ │"
  tput cup $((ptop+4)) $pleft; printf "└────┘"

  # Labels to the right of profile square
  local info_left=$((pleft+10))
  tput cup $((ptop+0)) $info_left; printf "${HGRN}Profile:${RESET} Hive Operator"
  tput cup $((ptop+1)) $info_left; printf "${HGRN}Mode:${RESET} ${HPRP}Active${RESET}"
  tput cup $((ptop+2)) $info_left; printf "${HGRN}Date:${RESET} $(date '+%Y-%m-%d %H:%M')"
  tput cup $((ptop+3)) $info_left; printf "${HGRN}Node:${RESET} Termux@$(uname -n)"

  # Notes area header
  local notes_top=$((top+7)) notes_left=$((left+2)) notes_w=$((box_w-4))
  tput cup $notes_top $notes_left
  printf "${HYLW}${RESET} [ edit ${HYLW} nano ~/.hive_ops.txt${RESET} ]"

  # Notes box (light divider)
  tput cup $((notes_top+1)) $notes_left
  printf "─%.0s" $(seq 1 $((notes_w)))

  # Print up to notes_rows lines from ~/.hive_ops.txt (without leading '# ' comments)
  local i=0 line
  while IFS= read -r line && [ $i -lt $notes_rows ]; do
    # Strip only the leading '# ' to let you keep commented examples if you like
    line="${line/#\# /}"
    tput cup $((notes_top+1+i+1)) $notes_left
    printf "%-${notes_w}.${notes_w}s" "$line"
    i=$((i+1))
  done < "$HOME/.hive_ops.txt"

  # Helpful quick-keys
  # Return cursor to prompt area (just below the banner)
  tput rc
  tput cup $((top+box_h+2)) 0
}

# Draw the banner on interactive shells only
case $- in
  *i*) hive_ops_banner ;;
esac
# ===== End Hive Ops Banner =====
