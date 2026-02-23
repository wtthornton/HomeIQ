#!/bin/bash
# Rollback script for tenacity migration
# Service: proactive-agent-service
# Created: 2026-02-05T14:19:22.952547

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\proactive-agent-service"
BACKUP_DIR="C:\cursor\HomeIQ\services\proactive-agent-service\.migration_backup_tenacity_20260205_141912"

echo "Rolling back tenacity migration for proactive-agent-service..."

# Restore requirements.txt
if [ -f "$BACKUP_DIR/requirements.txt" ]; then
    cp "$BACKUP_DIR/requirements.txt" "$SERVICE_DIR/requirements.txt"
    echo "[OK] Restored requirements.txt"
fi

# Restore src directory
if [ -d "$BACKUP_DIR/src" ]; then
    rm -rf "$SERVICE_DIR/src"
    cp -r "$BACKUP_DIR/src" "$SERVICE_DIR/src"
    echo "[OK] Restored src directory"
fi

echo "[OK] Rollback complete"
echo "Run 'docker-compose build proactive-agent-service' to rebuild with old versions"
