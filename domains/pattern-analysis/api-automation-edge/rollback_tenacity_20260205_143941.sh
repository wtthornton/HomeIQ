#!/bin/bash
# Rollback script for tenacity migration
# Service: api-automation-edge
# Created: 2026-02-05T14:39:41.298327

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\api-automation-edge"
BACKUP_DIR="C:\cursor\HomeIQ\services\api-automation-edge\.migration_backup_tenacity_20260205_143941"

echo "Rolling back tenacity migration for api-automation-edge..."

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
echo "Run 'docker-compose build api-automation-edge' to rebuild with old versions"
