#!/bin/bash
# Add this to .bashrc to run on startup
if pgrep -f "hive/app.py" > /dev/null; then
    echo "Hive Dashboard is already running."
else
    echo "Starting Hive Dashboard..."
    nohup ~/.hive_venv/bin/python3 ~/hive/app.py > /dev/null 2>&1 &
fi
