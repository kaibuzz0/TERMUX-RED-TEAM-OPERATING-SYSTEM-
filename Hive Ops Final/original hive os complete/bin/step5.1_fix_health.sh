#!/usr/bin/env bash
set -Eeuo pipefail
ts()  { date +%Y%m%d-%H%M%S; }
bak() { local f="$1"; [ -e "$f" ] && cp -f -- "$f" "$f.bak.$(ts)"; }

HIVE_BIN="${HIVE_BIN:-$HOME/hive/bin}"

# 1) hive_services.sh — make health return nonzero on probe failure
srv="$HIVE_BIN/hive_services.sh"
bak "$srv"
awk '
  BEGIN{skip=0;done=0}
  /^[[:space:]]*health\)[[:space:]]*$/ && !done {
    print "  health)"
    print "    socks=\"$(active_socks)\""
    print "    rc=0"
    print "    if ! socks_ok \"$socks\"; then"
    print "      log \"SOCKS down at $socks\""
    print "      exit 1"
    print "    fi"
    print "    set -- $(list)"
    print "    for s in \"$@\"; do"
    print "      probe_one \"$s\" || rc=2"
    print "    done"
    print "    exit \"$rc\""
    print "    ;;"
    skip=1; done=1; next
  }
  skip && /^[[:space:]]*;;[[:space:]]*$/ { skip=0; next }
  !skip { print }
' "$srv" > "$srv.tmp" && mv "$srv.tmp" "$srv"
chmod +x "$srv"

# 2) hive — print ALL GREEN only when health succeeds
cli="$HIVE_BIN/hive"
bak "$cli"
awk '
  BEGIN{skip=0;done=0}
  /^[[:space:]]*health\)[[:space:]]*$/ && !done {
    print "  health)"
    print "    m=\"$(read_mode)\"; s=\"$(active_socks)\""
    print "    echo \"[health] mode=${m} socks=${s}\""
    print "    if [[ \"$m\" == \"off\" ]]; then"
    print "      echo \"[health] NET: DISABLED (mode=off)\""
    print "      \"$HIVE_BIN/hive_services.sh\" status || true"
    print "      exit 0"
    print "    fi"
    print "    \"$HIVE_BIN/hive_net.sh\" status >/dev/null || true"
    print "    echo \"[health] Services…\""
    print "    if \"$HIVE_BIN/hive_services.sh\" health; then"
    print "      echo \"[health] ALL GREEN\""
    print "    else"
    print "      echo \"[health] ISSUES DETECTED (see lines above)\""
    print "      exit 1"
    print "    fi"
    print "    ;;"
    skip=1; done=1; next
  }
  skip && /^[[:space:]]*;;[[:space:]]*$/ { skip=0; next }
  !skip { print }
' "$cli" > "$cli.tmp" && mv "$cli.tmp" "$cli"
chmod +x "$cli"

# 3) (Optional) watchdog auto-resume when SOCKS back
#     Set HIVE_AUTOSTART_SERVICES=1 in env.sh to enable.
wd="$HIVE_BIN/hive_watchdog.sh"
bak "$wd"
awk '
  BEGIN{replaced=0}
  {
    if (!replaced && $0 ~ /^[[:space:]]*if[[:space:]]+socks_ok[[:space:]]*\(/) {
      print $0
      getline; # read the next line (likely the old log)
      print "    log \"socks OK at $socks\""
      print "    if [[ \"${HIVE_AUTOSTART_SERVICES:-0}\" -eq 1 ]]; then"
      print "      \"$HIVE_BIN/hive_services.sh\" ensure >/dev/null 2>&1 || true"
      print "    else"
      print "      \"$HIVE_BIN/hive_services.sh\" health >/dev/null 2>&1 || true"
      print "    fi"
      replaced=1
    } else {
      print $0
    }
  }
' "$wd" > "$wd.tmp" && mv "$wd.tmp" "$wd"
chmod +x "$wd"

echo "[step5.1] Patched:"
echo "  - $(basename "$srv") health exit codes"
echo "  - $(basename "$cli") health success/failed banner"
echo "  - $(basename "$wd") optional auto-resume hook (toggle via \$HIVE_AUTOSTART_SERVICES)"
