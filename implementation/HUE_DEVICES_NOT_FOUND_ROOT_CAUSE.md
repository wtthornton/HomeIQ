# Root Cause: Why AI Says "No Hue Lights" When You Have Hue Devices

**Date:** November 17, 2025  
**Status:** Root Cause Identified

## Problem

When you prompt: *"In the office, flash all the Hue lights for 45 secs..."*

The AI responds: *"It seems there are no Hue lights listed in your available devices."*

**But you DO have Hue devices!**

## Root Cause Analysis

### The Issue Chain

1. **Database is Empty (0 entities)**
   - SQLite database at `services/data-api/data/metadata.db` has 0 entities
   - Discovery service has never successfully stored entities
   - This is confirmed by: `python scripts/check_device_names.py` returns empty

2. **AI Service Queries Empty Database**
   - In `ask_ai_router.py` lines 4088-4089, the AI service queries:
     ```python
     devices_result = await data_api_client.fetch_devices(limit=100)
     entities_result = await data_api_client.fetch_entities(limit=200)
     ```
   - These queries return empty lists because database has 0 entities

3. **Clarification Detector Sees No Devices**
   - Line 4146: `available_devices=automation_context`
   - `automation_context` is built from empty database queries
   - Clarification detector sees no Hue devices → asks "Do you have Hue lights?"

### Code Flow

```
User Prompt → Ask AI Endpoint
    ↓
Extract Entities (from query text)
    ↓
Query Data-API for Available Devices/Entities  ← EMPTY (0 entities)
    ↓
Build automation_context (empty)
    ↓
Clarification Detector checks available_devices  ← EMPTY
    ↓
Detects: "No Hue lights found"
    ↓
Asks: "Do you have Hue lights set up?"
```

## Why Database is Empty

### Discovery Service Connection Failure

The discovery service cannot connect to data-api to store entities:

```
❌ Error posting devices to data-api: Cannot connect to host data-api:8006 ssl:default
❌ Error posting entities to data-api: Cannot connect to host data-api:8006
```

**Root Cause:** SSL connection issue in `discovery_service.py`
- Uses `aiohttp.TCPConnector(ssl=False)` but still tries SSL
- Connection works via curl but fails via aiohttp

### Discovery Never Runs Successfully

- Discovery can be triggered: `POST /api/v1/discovery/trigger`
- But entities are never stored because connection fails
- Result: Database remains empty

## Solution

### Immediate Fix: Get Entities into Database

1. **Fix Discovery Service Connection**
   - Resolve SSL connection issue in `discovery_service.py`
   - Or use HTTP client that doesn't require SSL for internal connections

2. **Trigger Discovery Successfully**
   - Once connection is fixed, trigger discovery
   - Verify entities are stored: `python scripts/check_device_names.py`

3. **Verify AI Service Can Query Entities**
   - After entities are in database, AI service will find them
   - Clarification detector will see Hue devices
   - No more "no Hue lights" message

### Long-term Fix: Event Enrichment

Even after entities are in database, events written to InfluxDB won't have device names unless enrichment code is added.

## Verification Steps

1. **Check Database:**
   ```bash
   python scripts/check_device_names.py
   # Should show Hue entities if discovery worked
   ```

2. **Check Discovery:**
   ```bash
   curl -X POST http://localhost:8001/api/v1/discovery/trigger
   # Check logs for "✅ Stored X entities to SQLite"
   ```

3. **Check AI Service:**
   ```bash
   python scripts/test_ask_ai_hue_lights.py
   # Should find Hue entities after database is populated
   ```

## Files Involved

1. `services/websocket-ingestion/src/discovery_service.py` - Discovery service (connection issue)
2. `services/ai-automation-service/src/api/ask_ai_router.py` - AI service (queries database)
3. `services/data-api/data/metadata.db` - SQLite database (currently empty)

## Test Script

Created `scripts/test_ask_ai_hue_lights.py` to verify:
- Services are running
- Hue entities exist in database
- AI service can query entities
- Ask AI request works
- Response doesn't say "no Hue lights"

## Next Steps

1. ✅ **Created E2E test script** - `scripts/test_ask_ai_hue_lights.py`
2. ⏳ **Fix discovery connection** - Resolve SSL issue
3. ⏳ **Trigger discovery** - Get entities into database
4. ⏳ **Verify test passes** - Run E2E test again

