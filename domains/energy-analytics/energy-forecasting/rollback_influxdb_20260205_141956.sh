#!/bin/bash
# Rollback script for InfluxDB migration
# Service: energy-forecasting
# Created: 2026-02-05T14:19:56.868110

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\energy-forecasting"
BACKUP_DIR="C:\cursor\HomeIQ\services\energy-forecasting\.migration_backup_influxdb_20260205_141956"

echo "Rolling back InfluxDB migration for energy-forecasting..."

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
echo "Run 'docker-compose build energy-forecasting' to rebuild with old versions"
