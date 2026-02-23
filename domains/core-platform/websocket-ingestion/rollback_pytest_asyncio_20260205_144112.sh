#!/bin/bash
# Rollback script for pytest-asyncio migration
# Service: websocket-ingestion
# Created: 2026-02-05T14:41:12.381289

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\websocket-ingestion"
BACKUP_DIR="C:\cursor\HomeIQ\services\websocket-ingestion\.migration_backup_20260205_144111"

echo "Rolling back pytest-asyncio migration for websocket-ingestion..."

# Restore pytest.ini
if [ -f "$BACKUP_DIR/pytest.ini" ]; then
    cp "$BACKUP_DIR/pytest.ini" "$SERVICE_DIR/pytest.ini"
    echo "✅ Restored pytest.ini"
fi

# Restore requirements.txt
if [ -f "$BACKUP_DIR/requirements.txt" ]; then
    cp "$BACKUP_DIR/requirements.txt" "$SERVICE_DIR/requirements.txt"
    echo "✅ Restored requirements.txt"
fi

# Restore tests directory
if [ -d "$BACKUP_DIR/tests" ]; then
    rm -rf "$SERVICE_DIR/tests"
    cp -r "$BACKUP_DIR/tests" "$SERVICE_DIR/tests"
    echo "✅ Restored tests directory"
fi

echo "✅ Rollback complete"
echo "Run 'docker-compose build websocket-ingestion' to rebuild with old versions"
