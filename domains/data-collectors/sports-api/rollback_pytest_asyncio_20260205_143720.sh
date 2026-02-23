#!/bin/bash
# Rollback script for pytest-asyncio migration
# Service: sports-api
# Created: 2026-02-05T14:37:20.900058

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\sports-api"
BACKUP_DIR="C:\cursor\HomeIQ\services\sports-api\.migration_backup_20260205_143720"

echo "Rolling back pytest-asyncio migration for sports-api..."

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
echo "Run 'docker-compose build sports-api' to rebuild with old versions"
