# Post-Migration Checklist

**Date:** November 17, 2025  
**Migration:** 004_add_entity_name_fields_and_capabilities  
**Status:** ✅ Migration Applied Successfully

## ✅ Migration Verification

- [x] Migration script executed successfully
- [x] All migrations applied (001 → 002 → 003 → 004)
- [x] Database schema updated

## 🔄 Service Restart Required

The following services need to be restarted to use the new schema:

### 1. data-api Service
**Why:** To recognize the new Entity and Service model fields
**Command:**
```bash
# Docker Compose
docker-compose restart data-api

# Or if running directly
# Stop and restart the service
```

**Verification:**
- Check logs for successful startup
- Verify API endpoints return new fields (friendly_name, capabilities, etc.)

### 2. websocket-ingestion Service
**Why:** To trigger discovery and populate new entity fields (name, capabilities, services)
**Command:**
```bash
# Docker Compose
docker-compose restart websocket-ingestion

# Or if running directly
# Stop and restart the service
```

**Verification:**
- Check logs for "DISCOVERY COMPLETE" message
- Verify services are being discovered: "Services: X total services across Y domains"
- Verify entities are being stored with name fields

### 3. ai-automation-service Service
**Why:** To use the new entity information in prompts and YAML generation
**Command:**
```bash
# Docker Compose
docker-compose restart ai-automation-service

# Or if running directly
# Stop and restart the service
```

**Verification:**
- Check logs for successful startup
- Test Ask AI query to verify entity context includes new fields

## 🧪 Testing Checklist

After restarting services, verify the following:

### Entity Data Verification
- [ ] Query `/api/entities` endpoint and verify entities have `friendly_name` field
- [ ] Verify entities have `name`, `name_by_user`, `original_name` fields populated
- [ ] Check that `capabilities` and `available_services` are populated (may be empty initially until enrichment runs)

### Services Data Verification
- [ ] Query database to verify `services` table exists and has data
- [ ] Check that services are stored per domain (light, switch, climate, etc.)

### AI Automation Service Verification
- [ ] Test Ask AI query with device names
- [ ] Verify YAML generation includes available services in prompts
- [ ] Check that entity context JSON includes all new fields (name, capabilities, available_services, device metadata)

### Discovery Service Verification
- [ ] Check websocket-ingestion logs for services discovery
- [ ] Verify services are being stored: "✅ Stored X services to SQLite"
- [ ] Verify entities are being stored with name fields

## 📊 Database Verification Queries

Run these SQL queries to verify the migration:

```sql
-- Check entity table structure
PRAGMA table_info(entities);

-- Check if new columns exist
SELECT name, friendly_name, capabilities, available_services 
FROM entities 
LIMIT 5;

-- Check services table
SELECT domain, COUNT(*) as service_count 
FROM services 
GROUP BY domain 
ORDER BY service_count DESC;

-- Check entity name fields
SELECT entity_id, name, name_by_user, original_name, friendly_name 
FROM entities 
WHERE friendly_name IS NOT NULL 
LIMIT 10;
```

## 🐛 Troubleshooting

### Entities don't have friendly_name
- **Cause:** Discovery hasn't run yet or entity registry doesn't have name fields
- **Fix:** Restart websocket-ingestion to trigger discovery
- **Verify:** Check HA Entity Registry has name fields set

### Services table is empty
- **Cause:** Discovery hasn't run yet or HA Services API unavailable
- **Fix:** Restart websocket-ingestion to trigger discovery
- **Verify:** Check websocket-ingestion logs for "✅ Retrieved X service domains from HA"

### Capabilities are empty
- **Cause:** Entity capability enrichment hasn't run yet
- **Fix:** This is expected initially - capabilities are enriched separately from State API
- **Note:** Capabilities will be populated when entities are enriched with state data

## 📝 Next Steps

1. **Restart all three services** (data-api, websocket-ingestion, ai-automation-service)
2. **Wait for discovery to complete** (check websocket-ingestion logs)
3. **Test Ask AI query** to verify new entity information is being used
4. **Monitor logs** for any errors related to new fields

## ✅ Success Criteria

Migration is successful when:
- ✅ All services restart without errors
- ✅ Entities have friendly_name populated
- ✅ Services table has data
- ✅ Ask AI queries use correct entity names
- ✅ YAML generation includes available services

