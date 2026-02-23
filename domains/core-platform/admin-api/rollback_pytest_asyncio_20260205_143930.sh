#!/bin/bash
# Rollback script for pytest-asyncio migration
# Service: admin-api
# Created: 2026-02-05T14:39:30.450068

set -e

SERVICE_DIR="C:\cursor\HomeIQ\services\admin-api"
BACKUP_DIR="C:\cursor\HomeIQ\services\admin-api\.migration_backup_20260205_143930"

echo "Rolling back pytest-asyncio migration for admin-api..."

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
echo "Run 'docker-compose build admin-api' to rebuild with old versions"
