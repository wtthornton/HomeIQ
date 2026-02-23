#!/bin/bash
# Rollback script for tenacity migration
# Service: rag-service
# Created: 2026-02-05T14:08:28.397407

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\rag-service"
BACKUP_DIR="C:\cursor\HomeIQ\services\rag-service\.migration_backup_tenacity_20260205_140822"

echo "Rolling back tenacity migration for rag-service..."

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
echo "Run 'docker-compose build rag-service' to rebuild with old versions"
