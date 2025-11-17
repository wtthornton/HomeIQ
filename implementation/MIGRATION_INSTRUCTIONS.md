# Database Migration Instructions

**Date:** November 17, 2025  
**Migration:** 004_add_entity_name_fields_and_capabilities

## Migration Overview

This migration adds the following to the `entities` table:
- Entity Registry name fields: `name`, `name_by_user`, `original_name`, `friendly_name`
- Entity capabilities: `supported_features`, `capabilities`, `available_services`
- Entity attributes: `icon`, `device_class`, `unit_of_measurement`
- Timestamp: `updated_at`
- Indexes: `idx_entity_friendly_name`, `idx_entity_supported_features`, `idx_entity_device_class`

This migration also creates a new `services` table for storing HA services.

## Running the Migration

### Option 1: Using Alembic Command (Recommended)

```bash
cd services/data-api
python -m alembic upgrade head
```

### Option 2: Using Docker (if running in containers)

```bash
docker exec -it homeiq-data-api python -m alembic upgrade head
```

### Option 3: Manual SQL (if Alembic fails)

If the migration script fails, you can run the SQL manually:

```sql
-- Add Entity Registry Name Fields
ALTER TABLE entities ADD COLUMN name TEXT;
ALTER TABLE entities ADD COLUMN name_by_user TEXT;
ALTER TABLE entities ADD COLUMN original_name TEXT;
ALTER TABLE entities ADD COLUMN friendly_name TEXT;

-- Add Entity Capabilities
ALTER TABLE entities ADD COLUMN supported_features INTEGER;
ALTER TABLE entities ADD COLUMN capabilities TEXT;  -- JSON stored as TEXT
ALTER TABLE entities ADD COLUMN available_services TEXT;  -- JSON stored as TEXT

-- Add Entity Attributes
ALTER TABLE entities ADD COLUMN icon TEXT;
ALTER TABLE entities ADD COLUMN device_class TEXT;
ALTER TABLE entities ADD COLUMN unit_of_measurement TEXT;

-- Add updated_at timestamp
ALTER TABLE entities ADD COLUMN updated_at DATETIME;

-- Create indexes
CREATE INDEX idx_entity_friendly_name ON entities(friendly_name);
CREATE INDEX idx_entity_supported_features ON entities(supported_features);
CREATE INDEX idx_entity_device_class ON entities(device_class);

-- Create services table
CREATE TABLE services (
    domain TEXT NOT NULL,
    service_name TEXT NOT NULL,
    name TEXT,
    description TEXT,
    fields TEXT,  -- JSON stored as TEXT
    target TEXT,  -- JSON stored as TEXT
    last_updated DATETIME,
    PRIMARY KEY (domain, service_name)
);

CREATE INDEX idx_services_domain ON services(domain);
```

## Verification

After running the migration, verify it worked:

```bash
# Check migration status
cd services/data-api
python -m alembic current

# Should show: 004 (head)
```

Or check the database directly:

```sql
-- Check if new columns exist
PRAGMA table_info(entities);

-- Check if services table exists
SELECT name FROM sqlite_master WHERE type='table' AND name='services';
```

## Rollback (if needed)

If you need to rollback:

```bash
cd services/data-api
python -m alembic downgrade -1
```

## Post-Migration Steps

1. **Restart data-api service** to ensure it recognizes the new schema
2. **Restart websocket-ingestion service** to trigger discovery and populate new fields
3. **Restart ai-automation-service** to use the new entity information

## Troubleshooting

### Error: "no such column: friendly_name"
- Migration didn't run successfully
- Check migration status: `python -m alembic current`
- Run migration: `python -m alembic upgrade head`

### Error: "table services already exists"
- Migration partially ran
- Check if you need to rollback and re-run: `python -m alembic downgrade -1 && python -m alembic upgrade head`

### Error: "database is locked"
- Another process is using the database
- Stop all services that use the database
- Run migration again

