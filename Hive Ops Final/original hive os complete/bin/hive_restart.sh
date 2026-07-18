#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
"$HOME/hive/bin/hive" stop
"$HOME/hive/bin/hive" start
