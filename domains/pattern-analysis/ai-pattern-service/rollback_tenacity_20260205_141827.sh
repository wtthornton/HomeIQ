#!/bin/bash
# Rollback script for tenacity migration
# Service: ai-pattern-service
# Created: 2026-02-05T14:18:27.052610

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\ai-pattern-service"
BACKUP_DIR="C:\cursor\HomeIQ\services\ai-pattern-service\.migration_backup_tenacity_20260205_141815"

echo "Rolling back tenacity migration for ai-pattern-service..."

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
echo "Run 'docker-compose build ai-pattern-service' to rebuild with old versions"
