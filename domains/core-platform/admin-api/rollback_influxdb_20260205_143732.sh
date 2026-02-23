#!/bin/bash
# Rollback script for InfluxDB migration
# Service: admin-api
# Created: 2026-02-05T14:37:32.060494

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\admin-api"
BACKUP_DIR="C:\cursor\HomeIQ\services\admin-api\.migration_backup_influxdb_20260205_143731"

echo "Rolling back InfluxDB migration for admin-api..."

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
echo "Run 'docker-compose build admin-api' to rebuild with old versions"
