#!/bin/bash
# Rollback script for tenacity migration
# Service: device-intelligence-service
# Created: 2026-02-05T14:18:45.181533

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\device-intelligence-service"
BACKUP_DIR="C:\cursor\HomeIQ\services\device-intelligence-service\.migration_backup_tenacity_20260205_141836"

echo "Rolling back tenacity migration for device-intelligence-service..."

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
echo "Run 'docker-compose build device-intelligence-service' to rebuild with old versions"
