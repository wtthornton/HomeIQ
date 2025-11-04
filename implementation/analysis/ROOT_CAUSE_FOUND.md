# Root Cause: Nightly Job Suggestions Not Being Created

**Date:** 2025-11-04  
**Status:** ROOT CAUSE IDENTIFIED

## Problem Summary

The nightly job is **running successfully** but **not creating suggestions** because it's finding **zero events** in the database.

## Evidence

### Scheduler Status
- **Last Job Run:** 2025-11-04T04:58:21.127831+00:00
- **Status:** `"no_data"`
- **Events Count:** `0`
- **Devices Checked:** 96
- **Next Run:** 2025-11-05T03:00:00+00:00

### Code Analysis

In `daily_analysis.py` lines 208-212:

```python
if events_df.empty:
    logger.warning("❌ No events available for analysis")
    job_result['status'] = 'no_data'
    job_result['events_count'] = 0
    return  # ← JOB EXITS EARLY, NO SUGGESTIONS CREATED
```

The job fetches events from the last 30 days (line 201):
```python
start_date = datetime.now(timezone.utc) - timedelta(days=30)
events_df = await data_client.fetch_events(
    start_time=start_date,
    limit=100000
)
```

If no events are found, the job exits early and **never reaches the suggestion generation phase**.

## Current State

### Existing Suggestions
- **Total:** 2 suggestions in database
- **Status:** 1 draft, 1 deployed
- **Created:** Both from Oct 31, 2025 (5 days ago)
- **Pattern ID:** Both are `null` (manually created, not from nightly job)

### Why No New Suggestions?

1. ✅ Scheduler is running (3 AM daily)
2. ✅ Job is executing
3. ✅ Device capability check works (96 devices checked)
4. ❌ **No event data found** → Job exits early
5. ❌ **No suggestions generated**

## Root Cause

The nightly job cannot find any event data in InfluxDB for the last 30 days. This could be due to:

1. **No events being ingested** - websocket-ingestion service not working
2. **InfluxDB query issue** - data-api service not querying correctly
3. **Data retention** - events older than expected or deleted
4. **Bucket/measurement mismatch** - wrong bucket or measurement name
5. **Time range issue** - query looking in wrong time range

## Next Steps to Fix

### 1. Verify Event Ingestion
Check if events are being stored in InfluxDB:
```bash
# Check websocket-ingestion service logs
docker logs homeiq-websocket --tail 50

# Check if events are in InfluxDB
# (Need to query InfluxDB directly or check data-api)
```

### 2. Check Data API Connection
Verify the data-api service can fetch events:
```bash
# Test data-api endpoint
curl http://localhost:8006/api/events?limit=10
```

### 3. Verify InfluxDB Configuration
Check that the ai-automation-service is using the correct:
- InfluxDB URL
- Bucket name
- Token/credentials
- Time range query

### 4. Check Service Logs
Look for errors in the nightly job execution:
```bash
docker logs ai-automation-service | grep -i "event\|no_data\|Phase 2"
```

## Immediate Action

The nightly job is working correctly, but it needs event data to generate suggestions. The issue is upstream - either events aren't being ingested, or the query isn't finding them.

## Files Involved

- `services/ai-automation-service/src/scheduler/daily_analysis.py:201-212` - Event fetching logic
- `services/ai-automation-service/src/clients/data_api_client.py` - Data API client
- `services/websocket-ingestion/` - Event ingestion service
- `services/data-api/` - Data query service

