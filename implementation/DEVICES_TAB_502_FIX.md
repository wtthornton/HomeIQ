# Devices Tab 502 Bad Gateway Fix

## Issue Summary
The Devices tab at `http://localhost:3000/devices` was showing a 502 Bad Gateway error.

## Root Cause
The `DataApiClient` in the health dashboard was configured to use `http://localhost:8006` as the base URL, which caused the browser to make direct requests to the data-api service. This failed due to:
1. CORS restrictions
2. Browser connectivity issues
3. Missing nginx proxy routing

The correct architecture is:
- Browser → nginx (port 3000) → data-api (port 8006)
- NOT: Browser → data-api (port 8006) directly

## Changes Made

### 1. `services/health-dashboard/src/services/api.ts`
**Line 257-259**: Changed the `DataApiClient` constructor to use an empty base URL:
```typescript
// BEFORE
const DATA_API_URL = import.meta.env.VITE_DATA_API_URL || 'http://localhost:8006';
super(DATA_API_URL);

// AFTER  
const DATA_API_URL = import.meta.env.VITE_DATA_API_URL || '';
super(DATA_API_URL);
```

This makes the client use relative URLs that get proxied by nginx.

### 2. `docker-compose.yml`
**Line 679**: Set `VITE_DATA_API_URL` to empty string:
```yaml
environment:
  - VITE_API_BASE_URL=http://localhost:8003
  - VITE_DATA_API_URL=  # Empty for nginx proxy routing
  - VITE_WS_URL=ws://localhost:8001/ws
  - VITE_ENVIRONMENT=production
```

## How It Works Now

1. Browser makes request to `/api/devices` (relative URL)
2. nginx receives request at `http://localhost:3000/api/devices`
3. nginx proxy rule (line 44-50 in `nginx.conf`) routes to `http://homeiq-data-api:8006/api/devices`
4. data-api service responds
5. nginx returns response to browser

## Verification
- ✅ `curl http://localhost:8006/api/devices` - Direct API works
- ✅ `curl http://localhost:3000/api/devices` - Via nginx proxy works
- ✅ Browser loads Devices tab successfully with 94 devices

## Files Modified
1. `services/health-dashboard/src/services/api.ts`
2. `docker-compose.yml`

## Deployment
The fix required rebuilding the health-dashboard container:
```bash
docker-compose up -d --build health-dashboard
```

