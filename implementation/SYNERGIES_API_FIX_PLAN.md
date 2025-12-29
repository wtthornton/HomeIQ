# Synergies API 404 Error - Fix Plan

## Problem
The `/api/synergies/stats` endpoint returns 404, causing the Synergies page to show an error banner.

## Root Cause Analysis

1. **Frontend calls**: `/api/synergies` and `/api/synergies/stats`
2. **Nginx proxy**: Routes to `ai-automation-service-new:8025/api/synergies*`
3. **Automation service**: Proxies to `ai-pattern-service:8020/api/v1/synergies*`
4. **Pattern service**: Has routes defined but `/stats` returns 404

## Current Status

- ✅ `/api/synergies/list` works correctly
- ❌ `/api/synergies/stats` returns 404
- ✅ Routes are registered: `/api/v1/synergies/stats` exists
- ❌ FastAPI is matching `/{synergy_id}` before `/stats`

## Issue

FastAPI route matching order: The parameterized route `/{synergy_id}` is matching `/stats` before the specific route `/stats` is matched, even though `specific_router` (with `/stats`) is registered before `router` (with `/{synergy_id}`).

## Solution

The `/stats` route is defined on `specific_router` which is registered first, but FastAPI is still matching the parameterized route first. This is a known FastAPI behavior where parameterized routes can match before specific routes.

**Fix**: Ensure the specific route is matched by:
1. Removing the guard in the parameterized route (already done)
2. Verifying route registration order (already correct)
3. Testing if the route handler is actually being called

## Next Steps

1. Add debug logging to the `/stats` route handler to verify it's being called
2. Check if there's a middleware or other interference
3. Consider using a different route structure if needed

## Files Modified

- `services/ai-pattern-service/src/api/synergy_router.py` - Removed duplicate `/stats` route from main router, removed guard from parameterized route

