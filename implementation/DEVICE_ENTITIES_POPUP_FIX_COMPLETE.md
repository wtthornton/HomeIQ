# Device Entities Popup Fix - Complete

**Date:** January 6, 2025  
**Status:** ✅ FIXED  
**Issue:** Popup showed 0 entities instead of 4 for Presence-Sensor-FP2-8B8A

## Root Cause

**Nginx was stripping query parameters** when proxying `/api/entities` requests to the data-api service. The nginx configuration used:
```nginx
proxy_pass http://data_api/api/entities;
```

When nginx uses `proxy_pass` with a path, it replaces the entire URI path, which can cause query parameters to be lost in certain configurations.

## Solution

Changed nginx configuration to use `$request_uri` which preserves the full URI including query string:

```nginx
location /api/entities {
    # Use $request_uri to preserve full URI including query string
    proxy_pass http://data_api$request_uri;
    # ... rest of proxy settings
}
```

## Verification

✅ **API Test:** Direct call returns 4 entities correctly  
✅ **Through Nginx:** Now returns 4 entities correctly  
✅ **Frontend Console:** Shows "Loaded 4 entities"  
✅ **Browser:** Popup displays correct entity count

## Files Modified

1. `services/health-dashboard/nginx.conf` - Fixed query parameter passing
2. `services/data-api/src/devices_endpoints.py` - Added debug logging and Request parameter (for future debugging)

## Testing

```bash
# Test direct API (bypass nginx)
curl "http://localhost:8006/api/entities?limit=5&device_id=07765655ee253761bb57e33b0b04aa6b"
# Returns: 4 entities ✅

# Test through nginx proxy
curl "http://localhost:3000/api/entities?limit=5&device_id=07765655ee253761bb57e33b0b04aa6b"
# Returns: 4 entities ✅ (was 100 before fix)
```

## Related Issues

- Main device list correctly showed "4 entities" (SQL JOIN query worked)
- Popup incorrectly showed "Entities (0)" because API call failed to filter by device_id
- Frontend correctly filtered out mismatched entities, but API wasn't returning filtered results

## Deployment

✅ Rebuilt and restarted `health-dashboard` container  
✅ Changes are live and working

