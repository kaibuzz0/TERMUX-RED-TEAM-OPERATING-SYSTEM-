#!/data/data/com.termux/files/usr/bin/bash
if command -v am >/dev/null 2>&1; then
  if ! am start -n org.torproject.android/.OrbotMainActivity >/dev/null 2>&1; then
    echo "[orbot-ui] Cannot launch Orbot UI. Open manually and start Tor (SOCKS 9050)."
  fi
else
  echo "[orbot-ui] Android Activity Manager not present. Launch Orbot manually."
fi
