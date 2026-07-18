#!/bin/bash
# Mega Man Master Switch
# Routes all activity through Tor via Proxychains

TOR_STATUS=$(pgrep tor)

if [ -z "$TOR_STATUS" ]; then
    echo "Starting Tor..."
    tor &
    sleep 5
else
    echo "Tor is already running."
fi

echo "Mega Man mode active. Routing through Proxychains..."
proxychains4 "$@"
