#!/bin/bash
# Backup all databases and configurations for HomeIQ system
# Usage: ./scripts/backup-all.sh

set -e  # Exit on error

BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Starting backup to $BACKUP_DIR..."

# Backup InfluxDB
echo "📊 Backing up InfluxDB..."
if docker exec homeiq-influxdb influx version > /dev/null 2>&1; then
    docker exec homeiq-influxdb influx backup "/backup/influxdb-$(date +%Y%m%d-%H%M%S)" || echo "⚠️  InfluxDB backup failed (may need manual backup)"
else
    echo "⚠️  InfluxDB container not running, skipping backup"
fi

# Backup SQLite databases
echo "💾 Backing up SQLite databases..."

# metadata.db (data-api)
if docker exec homeiq-data-api sqlite3 /app/data/metadata.db "SELECT 1;" > /dev/null 2>&1; then
    docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".backup $BACKUP_DIR/metadata.db" || echo "⚠️  metadata.db backup failed"
    echo "✅ metadata.db backed up"
else
    echo "⚠️  data-api container not running or database not accessible"
fi

# ai_automation.db (ai-automation-service)
if docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db "SELECT 1;" > /dev/null 2>&1; then
    docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".backup $BACKUP_DIR/ai_automation.db" || echo "⚠️  ai_automation.db backup failed"
    echo "✅ ai_automation.db backed up"
else
    echo "⚠️  ai-automation-service container not running or database not accessible"
fi

# Backup Docker volumes
echo "📦 Backing up Docker volumes..."

# InfluxDB volume
if docker volume inspect homeiq_influxdb_data > /dev/null 2>&1; then
    docker run --rm -v homeiq_influxdb_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf /backup/influxdb-volume.tar.gz -C /data . || echo "⚠️  InfluxDB volume backup failed"
    echo "✅ InfluxDB volume backed up"
else
    echo "⚠️  InfluxDB volume not found"
fi

# SQLite volume
if docker volume inspect homeiq_sqlite_data > /dev/null 2>&1; then
    docker run --rm -v homeiq_sqlite_data:/data -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf /backup/sqlite-volume.tar.gz -C /data . || echo "⚠️  SQLite volume backup failed"
    echo "✅ SQLite volume backed up"
else
    echo "⚠️  SQLite volume not found"
fi

# Backup configurations
echo "⚙️  Backing up configurations..."

# Docker Compose configuration
if [ -f docker-compose.yml ]; then
    cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml"
    echo "✅ docker-compose.yml backed up"
fi

# Environment files
if [ -f .env ]; then
    cp .env "$BACKUP_DIR/.env"
    echo "✅ .env backed up"
fi

# Container status
docker-compose ps > "$BACKUP_DIR/container-status.txt" 2>&1 || echo "⚠️  Could not get container status"
echo "✅ Container status backed up"

# Database schemas
echo "📋 Backing up database schemas..."

if docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".schema" > "$BACKUP_DIR/schema-metadata.sql" 2>&1; then
    echo "✅ metadata.db schema backed up"
fi

if docker exec homeiq-ai-automation-service sqlite3 /app/data/ai_automation.db ".schema" > "$BACKUP_DIR/schema-ai-automation.sql" 2>&1; then
    echo "✅ ai_automation.db schema backed up"
fi

# Create backup manifest
cat > "$BACKUP_DIR/manifest.txt" << EOF
HomeIQ System Backup
Date: $(date)
Backup Directory: $BACKUP_DIR

Contents:
- InfluxDB backup (if available)
- SQLite database backups
- Docker volume backups
- Configuration files
- Container status
- Database schemas

To restore:
1. Stop services: docker-compose down
2. Restore volumes from tar.gz files
3. Restore databases from .db files
4. Restore configurations
5. Start services: docker-compose up -d
EOF

echo "✅ Backup manifest created"

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "✅ Backup complete: $BACKUP_DIR"
echo "📊 Backup size: $BACKUP_SIZE"
echo ""
echo "📝 Backup manifest: $BACKUP_DIR/manifest.txt"

