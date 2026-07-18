#!/bin/bash
# Standardized logger for Hive OS
LOG_FILE="/root/hive/logs/system.log"

log() {
    local level=$1
    local message=$2
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $message" >> "$LOG_FILE"
}

case $1 in
    info) log "INFO" "$2" ;;
    warn) log "WARN" "$2" ;;
    error) log "ERROR" "$2" ;;
    *) log "INFO" "$1" ;;
esac
