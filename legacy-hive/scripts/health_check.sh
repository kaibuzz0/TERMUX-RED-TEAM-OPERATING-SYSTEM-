#!/bin/bash
# Basic health check for Hive OS environment
echo "Checking directory structure..."
DIRS=("/root/hive/projects" "/root/hive/docs" "/root/hive/logs" "/root/hive/scripts" "/root/hive/backups" "/root/hive/dashboard")
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Directory $dir does not exist."
        exit 1
    fi
done
echo "All directories exist."
exit 0
