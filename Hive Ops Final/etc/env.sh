# === HIVE OPS FINAL - Unified Environment v5.0 ===
# Works with both bash legacy and Python swarm layers
# Source this in .bashrc: source /path/to/Hive\ Ops\ Final/etc/env.sh

# Base paths - unified for both systems
export HIVE_HOME="${HIVE_HOME:-$HOME/hive}"
export HIVE_OS="${HIVE_OS:-/root/hive-os}"
export HIVE_SWARM="${HIVE_SWARM:-/root/hive-swarm}"
export HIVE_FINAL="${HIVE_FINAL:-$HOME/Hive Ops Final}"

# Subdirectories
export HIVE_BIN="$HIVE_HOME/bin"
export HIVE_ETC="$HIVE_HOME/etc"
export HIVE_LOG="$HIVE_HOME/logs"
export HIVE_STATE="$HIVE_HOME/state"

# Network configuration
export HIVE_PROXY_MODE="${HIVE_PROXY_MODE:-orbot}"
export HIVE_TOR_SOCKS_ORBOT="127.0.0.1:9050"
export HIVE_TOR_SOCKS_LOCAL="127.0.0.1:9052"
export HIVE_TOR_CONTROL="127.0.0.1:9051"

# Brain-Plug integration
export HIVE_ESCAPE_FILE="${HIVE_ESCAPE_FILE:-$HIVE_ETC/escape.txt}"

# PATH - prioritize new unified bin, then legacy
NEW_PATH="$HIVE_FINAL/bin:$HIVE_BIN:$HIVE_OS/bin"
case ":$PATH:" in
  *":$NEW_PATH:"*) : ;;
  *) export PATH="$NEW_PATH:$PATH" ;;
esac

# Python path for swarm modules
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$HIVE_SWARM:$HIVE_FINAL/lib"

# Features
export HIVE_AUTOSTART_SERVICES="${HIVE_AUTOSTART_SERVICES:-1}"
export HIVE_BOOT_ENABLE="${HIVE_BOOT_ENABLE:-1}"

# Aliases
alias hive="python3 '$HIVE_FINAL/bin/hive'"
alias health="hive health"
alias hstatus="hive status"
alias hnet="hive net"
alias hservices="hive services"
alias hdash="hive dashboard"

# Optional: dev tools
if [[ -f "$HIVE_ETC/dev.aliases.sh" ]]; then
    source "$HIVE_ETC/dev.aliases.sh"
fi
