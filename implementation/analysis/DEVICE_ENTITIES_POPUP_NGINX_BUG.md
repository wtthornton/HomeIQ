# Device Entities Popup - Nginx Query Parameter Bug

**Date:** January 6, 2025  
**Issue:** API returns 100 entities instead of 4 when called through nginx proxy  
**Root Cause:** Query parameters not being passed correctly through nginx to FastAPI

## Problem Summary

- **Direct API call (bypass nginx):** Returns 4 entities ✅
- **Through nginx proxy:** Returns 100 entities (ignores device_id filter) ❌
- **Frontend:** Shows 0 entities (correctly filters out 100 mismatched entities)

## Root Cause

The nginx `proxy_pass` directive with variables doesn't automatically append query parameters. When using `set $backend "http://..."; proxy_pass $backend/api/entities;`, the query string is lost.

## Solution

Changed nginx config to explicitly pass query parameters:
```nginx
proxy_pass $backend/api/entities$is_args$args;
```

However, this didn't fix the issue. The problem may be deeper - FastAPI may not be receiving the query parameter correctly.

## Investigation Steps

1. ✅ Confirmed API code correctly filters by device_id
2. ✅ Added debug logging to see what FastAPI receives
3. ✅ Fixed nginx config to explicitly pass query parameters
4. ⏳ Need to verify FastAPI is actually receiving the parameter

## Next Steps

1. Check FastAPI logs to see if device_id parameter is received
2. Test with curl directly to data-api (bypass nginx)
3. Consider using upstream block instead of variables
4. Check if there's a FastAPI/Pydantic issue with query parameter parsing

