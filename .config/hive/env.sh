# === Hive env (canonical) ===
export HIVE_HOME="$HOME/hive"
export HIVE_BIN="$HIVE_HOME/bin"
export HIVE_ETC="$HIVE_HOME/etc"
export HIVE_LOG="$HIVE_HOME/logs"
export HIVE_STATE="$HIVE_HOME/state"

# Net mode defaults: orbot | local | off
export HIVE_PROXY_MODE="${HIVE_PROXY_MODE:-orbot}"

# Orbot SOCKS (app-managed). No ControlPort.
export HIVE_TOR_SOCKS_ORBOT="127.0.0.1:9050"

# Local Tor (we bind SOCKSPort on 9052 to avoid Orbot collision)
export HIVE_TOR_SOCKS_LOCAL="127.0.0.1:9052"
export HIVE_TOR_CONTROL="127.0.0.1:9051"

# Canonical Hive speak
export HIVE_ESCAPE_FILE="$HIVE_ETC/escape.txt"

# PATH: prefer hive/bin early
case ":$PATH:" in
  *":$HIVE_BIN:"*) : ;;
  *) export PATH="$HIVE_BIN:$PATH" ;;
esac

# (No global ALL_PROXY/HTTP(S)_PROXY here — proxies applied by hive net/service wrappers)
# ============================
export HIVE_AUTOSTART_SERVICES=1
export HIVE_BOOT_ENABLE=1
