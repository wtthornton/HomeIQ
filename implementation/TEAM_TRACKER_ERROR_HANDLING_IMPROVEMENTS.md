# Team Tracker Error Handling Improvements

**Date:** January 2025  
**Status:** ✅ Completed  
**Issue:** Detection still showing failure without clear error messages

## Problem

Even after fixing the database query issue, the detection was still failing but not providing clear error messages to help diagnose the issue.

## Improvements Made

### 1. Enhanced Error Logging

**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**
- Added detailed logging at each step of the detection process
- Logs when querying data-api
- Logs number of entities received
- Logs each Team Tracker entity found
- Better warning messages when no entities found

**Before:**
```python
logger.info(f"Found {len(team_sensors)} Team Tracker sensors")
```

**After:**
```python
logger.info(f"Querying data-api at {data_api_client.base_url} for sensor entities...")
logger.info(f"Received {len(all_sensor_entities)} sensor entities from data-api")
logger.info(f"✅ Team Tracker entity detected: entity_id={entity_id}, platform={platform}")
logger.info(f"Found {len(team_sensors)} Team Tracker sensors from data-api")
```

### 2. Improved Data API Client Error Messages

**File:** `services/device-intelligence-service/src/clients/data_api_client.py`

**Changes:**
- Specific error handling for different HTTP error types
- Connection errors show clear message about service availability
- Timeout errors show timeout duration
- HTTP status errors include response details
- All errors wrapped in user-friendly messages

**Error Types Handled:**
- `HTTPStatusError`: Shows status code and response text
- `ConnectError`: Shows connection failure with service URL
- `TimeoutException`: Shows timeout duration
- Generic `HTTPError`: Shows general HTTP error
- Generic `Exception`: Shows unexpected errors

**Example Error Messages:**
```
"Could not connect to Data API at http://data-api:8006. Is the service running?"
"Data API returned 401: Unauthorized"
"Data API request timed out after 30 seconds"
```

### 3. Better Response Messages

**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**
- Response includes warning if data-api query failed
- Error messages in HTTPException include more context
- Distinguishes between connection errors and other errors

**Response Format:**
```python
{
    "detected_count": 0,
    "detected_teams": [],
    "integration_status": "not_installed",
    "warning": "Data-api query failed, used local database: Could not connect..."
}
```

### 4. Debug Information

**Changes:**
- When no entities found, attempts to get platform debug info
- Logs available sensor platforms from data-api
- Helps identify if Team Tracker entities exist but with different platform values

## Testing

To test error handling:

1. **Test with data-api down:**
   ```bash
   # Stop data-api service
   docker-compose stop data-api
   
   # Try detection
   curl -X POST http://localhost:8028/api/team-tracker/detect
   ```

2. **Check logs:**
   ```bash
   docker logs device-intelligence-service | grep -i "team tracker"
   ```

3. **Test with wrong URL:**
   ```bash
   # Set wrong DATA_API_URL
   export DATA_API_URL=http://wrong-host:8006
   ```

## Expected Behavior

### Success Case:
- Logs show: "Querying data-api...", "Received X entities...", "Found Y Team Tracker sensors"
- Response: `{"detected_count": Y, "detected_teams": [...], "integration_status": "detected"}`

### Failure Cases:

1. **Data-api not accessible:**
   - Logs: "Could not connect to Data API at http://data-api:8006. Is the service running?"
   - Falls back to local database
   - Response includes warning

2. **No Team Tracker entities:**
   - Logs: "No Team Tracker entities found"
   - Logs available platforms for debugging
   - Response: `{"detected_count": 0, "integration_status": "not_installed"}`

3. **Authentication error:**
   - Logs: "Data API returned 401: Unauthorized"
   - Error message includes status code and response

## Files Modified

1. `services/device-intelligence-service/src/clients/data_api_client.py`
   - Enhanced error handling with specific error types
   - User-friendly error messages

2. `services/device-intelligence-service/src/api/team_tracker_router.py`
   - Better logging throughout detection process
   - Improved error messages in responses
   - Warning messages in response when data-api fails

## Next Steps

1. Monitor logs to see actual error messages
2. Verify data-api service is accessible
3. Check if Team Tracker entities exist in Home Assistant
4. Use debug endpoint to see available platforms

