#!/bin/bash
# AUTO-PROJECT INITIATOR (Hive Swarm Architect)
# Simplifies creating new Hive-integrated projects.

PROJECT_NAME=$1

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: hive-init <project-name>"
    exit 1
fi

mkdir -p /root/projects/"$PROJECT_NAME"
cd /root/projects/"$PROJECT_NAME"
git init
echo "Initialized hive project: $PROJECT_NAME"
