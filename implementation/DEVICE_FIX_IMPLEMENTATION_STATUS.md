# Device Fix Implementation Status

**Date:** November 17, 2025  
**Status:** In Progress - Core Implementation Complete, Import Paths Need Fixing  
**Priority:** Critical

## ✅ Completed

### 1. Database Schema Updates
- ✅ Updated `Entity` model with new fields:
  - `name`, `name_by_user`, `original_name`, `friendly_name`
  - `supported_features`, `capabilities`, `available_services`
  - `icon`, `device_class`, `unit_of_measurement`
  - `updated_at` timestamp
- ✅ Created `Service` model for storing HA services
- ✅ Created migration script `004_add_entity_name_fields_and_capabilities.py`
- ✅ Updated model indexes

### 2. Data Ingestion Updates
- ✅ Updated `bulk_upsert_entities` to store name fields from Entity Registry
- ✅ Added `bulk_upsert_services` endpoint for storing HA services
- ✅ Updated `EntityResponse` model to include all new fields
- ✅ Updated API endpoints (`get_entity`, `list_entities`) to return new fields

### 3. HA Client Updates
- ✅ Added `get_services()` method to `HomeAssistantClient` to fetch HA Services API

### 4. New Services Created
- ✅ Created `EntityCapabilityEnrichment` service for enriching entities with capabilities
- ✅ Created `ServiceValidator` service for validating service calls

### 5. Entity Context Builder Updates
- ✅ Updated `build_entity_context_json` to accept `db_session` parameter
- ✅ Implemented database-first lookup pattern
- ✅ Added all name fields, capabilities, available_services, device metadata to context
- ✅ Updated all calls to pass `db_session`

## ⚠️ Needs Fixing

### Import Path Issues

The following files have incorrect import paths that need to be fixed:

1. **`services/ai-automation-service/src/prompt_building/entity_context_builder.py`**
   - Line 165: `from ...data_api.models import Entity, Device`
   - **Issue:** `data_api` module doesn't exist in ai-automation-service
   - **Fix Options:**
     - Option A: Access data-api database directly (requires separate connection)
     - Option B: Use DataAPIClient HTTP client to fetch entity data
     - Option C: Create shared models module

2. **`services/ai-automation-service/src/services/entity_capability_enrichment.py`**
   - Line 237: `from ...data_api.models import Entity`
   - **Same issue as above**

3. **`services/ai-automation-service/src/services/service_validator.py`**
   - Lines 52, 117, 181: `from ...data_api.models import Entity`
   - **Same issue as above**

### Recommended Fix

Since `db_session` passed to these functions is from ai-automation-service's own database (not data-api), we have two options:

**Option 1: Use DataAPIClient (Recommended)**
- Query entities via HTTP API instead of direct database access
- Pros: Clean separation, no shared database access
- Cons: Additional HTTP call overhead

**Option 2: Access data-api database directly**
- Create a separate database connection to data-api's SQLite database
- Pros: Direct access, faster
- Cons: Tight coupling, requires database path configuration

**Option 3: Pass entity data instead of db_session**
- Fetch entity data before calling these functions
- Pros: No import issues
- Cons: More data passing, less efficient

## 🔄 Remaining Tasks

### High Priority
1. **Fix import paths** in:
   - `entity_context_builder.py`
   - `entity_capability_enrichment.py`
   - `service_validator.py`

2. **Update YAML generation** to validate service calls:
   - Add service validation before YAML generation
   - Use `ServiceValidator` to check service calls against `available_services`

3. **Update entity enrichment** to use database-first lookup:
   - Modify `entity_attribute_service.py` to query database first
   - Store enriched data back to database

4. **Update discovery service** to fetch and store services:
   - Add `discover_services()` method to `DiscoveryService`
   - Call `bulk_upsert_services` after discovery

5. **Update entity validation context** to include available_services and device metadata

### Medium Priority
6. **Update UnifiedPromptBuilder** to include available_services and device metadata

7. **Run database migration** to apply schema changes

8. **Test all changes** with actual HA data

## 📝 Notes

- The database schema changes are complete and ready for migration
- All API endpoints have been updated to return new fields
- The core logic for database-first lookup is implemented but needs import path fixes
- Service validation logic is implemented but needs to be integrated into YAML generation

## Next Steps

1. Fix import paths (choose Option 1, 2, or 3 above)
2. Integrate service validation into YAML generation
3. Update discovery service to fetch services
4. Run migration and test

