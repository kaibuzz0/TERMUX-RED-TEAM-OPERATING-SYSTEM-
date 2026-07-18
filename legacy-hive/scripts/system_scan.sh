#!/bin/bash
# AUTO-BUILD SYSTEM SCANNER (Hive Swarm Architect)
# Scans system for dev tools and reports state for Hive.

echo "--- SYSTEM TOOL SCAN ---"
for tool in gcc clang rustc cargo make cmake pip python3 npm node git; do
    if command -v $tool >/dev/null 2>&1; then
        echo "$tool: FOUND"
    else
        echo "$tool: MISSING"
    fi
done
echo "--- SCAN COMPLETE ---"
