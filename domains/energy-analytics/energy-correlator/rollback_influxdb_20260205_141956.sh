#!/bin/bash
# Rollback script for InfluxDB migration
# Service: energy-correlator
# Created: 2026-02-05T14:19:56.703843

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\energy-correlator"
BACKUP_DIR="C:\cursor\HomeIQ\services\energy-correlator\.migration_backup_influxdb_20260205_141952"

echo "Rolling back InfluxDB migration for energy-correlator..."

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
echo "Run 'docker-compose build energy-correlator' to rebuild with old versions"
