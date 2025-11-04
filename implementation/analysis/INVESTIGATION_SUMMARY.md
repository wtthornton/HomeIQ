# Investigation Summary: Nightly Job Suggestions

**Date:** 2025-11-04  
**Status:** ✅ ROOT CAUSE IDENTIFIED

## Executive Summary

The nightly job **is running correctly** but **not creating suggestions** because it finds **zero events** in the database. The job exits early when no event data is available, preventing suggestion generation.

## Key Findings

### ✅ What's Working

1. **Scheduler is running** - Executes daily at 3 AM
2. **Service is healthy** - Running on port 8024
3. **API endpoints work** - All endpoints accessible
4. **Job execution** - Job runs successfully
5. **Device capability check** - 96 devices checked successfully

### ❌ What's Not Working

1. **No event data found** - Job finds 0 events in last 30 days
2. **Early exit** - Job exits before suggestion generation phase
3. **No new suggestions** - Last suggestions from Oct 31 (5 days ago)

## Root Cause

**Location:** `services/ai-automation-service/src/scheduler/daily_analysis.py:208-212`

```python
if events_df.empty:
    logger.warning("❌ No events available for analysis")
    job_result['status'] = 'no_data'
    job_result['events_count'] = 0
    return  # ← JOB EXITS HERE, NO SUGGESTIONS CREATED
```

The job queries for events from the last 30 days but finds none, so it exits early and never reaches the suggestion generation phase.

## Evidence

### Scheduler Status (from API)
```json
{
  "schedule": "0 3 * * *",
  "next_run": "2025-11-05T03:00:00+00:00",
  "is_running": false,
  "recent_jobs": [{
    "start_time": "2025-11-04T04:58:21.127831+00:00",
    "status": "no_data",
    "devices_checked": 96,
    "capabilities_updated": 0,
    "new_devices": 0,
    "events_count": 0  ← ZERO EVENTS
  }]
}
```

### Suggestions in Database
- **Total:** 2 suggestions
- **Last created:** Oct 31, 2025 (5 days ago)
- **Pattern ID:** Both are `null` (manually created, not from nightly job)
- **Status:** 1 draft, 1 deployed

## Next Steps to Fix

### 1. Verify Event Ingestion Pipeline

Check if events are being ingested into InfluxDB:

```bash
# Check websocket-ingestion service
docker logs homeiq-websocket --tail 100 | grep -i "event\|batch"

# Check data-api service
curl http://localhost:8006/api/events?limit=10
```

### 2. Check InfluxDB Configuration

Verify the ai-automation-service is configured correctly:
- InfluxDB URL: Should point to `http://influxdb:8086` (internal) or `http://localhost:8086` (external)
- Bucket name: Should be `home_assistant_events`
- Token: Should have read permissions
- Time range: Querying last 30 days correctly

### 3. Test Data API Connection

Manually test if the data-api can fetch events:

```bash
# Test from within the service container
docker exec ai-automation-service python -c "
from services.ai_automation_service.src.clients.data_api_client import DataAPIClient
import asyncio
from datetime import datetime, timedelta, timezone

async def test():
    client = DataAPIClient(base_url='http://homeiq-data-api:8006')
    start = datetime.now(timezone.utc) - timedelta(days=30)
    df = await client.fetch_events(start_time=start, limit=100)
    print(f'Found {len(df)} events')

asyncio.run(test())
"
```

### 4. Check Service Logs

Look for errors in the nightly job execution:

```bash
docker logs ai-automation-service | grep -i "Phase 2\|events\|no_data\|fetch_events"
```

## Files Involved

1. **Event Fetching:** `services/ai-automation-service/src/scheduler/daily_analysis.py:201-212`
2. **Data API Client:** `services/ai-automation-service/src/clients/data_api_client.py`
3. **Event Ingestion:** `services/websocket-ingestion/` (upstream service)
4. **Data API:** `services/data-api/` (upstream service)

## Conclusion

The nightly job is **functioning correctly** but cannot generate suggestions because there's **no event data** to analyze. The issue is **upstream** - either:

1. Events aren't being ingested by websocket-ingestion
2. Events aren't being stored in InfluxDB
3. The data-api query isn't finding events (wrong bucket/query)
4. Events exist but outside the 30-day window

**Action Required:** Investigate the event ingestion and storage pipeline to ensure events are being collected and stored in InfluxDB.

