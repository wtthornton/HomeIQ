#!/bin/bash
# HomeIQ PostgreSQL Backup Script
# Dumps each schema separately for granular restore capability.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${POSTGRES_USER:-homeiq}"
PG_DB="${POSTGRES_DB:-homeiq}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

SCHEMAS=(core automation agent blueprints energy devices patterns rag)

echo "=== PostgreSQL Backup - $TIMESTAMP ==="

# Full database dump
echo "Backing up full database..."
pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
    --format=custom --compress=6 \
    -f "$BACKUP_DIR/homeiq_full_${TIMESTAMP}.dump"
echo "Full backup: $BACKUP_DIR/homeiq_full_${TIMESTAMP}.dump"

# Per-schema dumps
for schema in "${SCHEMAS[@]}"; do
    echo "Backing up schema: $schema"
    pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        --schema="$schema" --format=custom --compress=6 \
        -f "$BACKUP_DIR/homeiq_${schema}_${TIMESTAMP}.dump"
done

# Cleanup old backups (keep 7 daily, 4 weekly)
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "homeiq_*.dump" -mtime +30 -delete 2>/dev/null || true

echo "Backup complete!"
ls -lh "$BACKUP_DIR"/homeiq_*_"${TIMESTAMP}".dump
