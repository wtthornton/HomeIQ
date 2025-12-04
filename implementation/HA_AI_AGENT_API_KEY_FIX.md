# HA AI Agent API Key Fix

## Issue
The AGENT page was showing "Missing X-HomeIQ-API-Key or Authorization header" errors because:
1. The `haAiAgentApi.ts` client was not adding authentication headers to requests
2. The nginx configuration was missing a proxy rule for `/api/ha-ai-agent` routes

## Fixes Applied

### 1. Updated `services/ai-automation-ui/src/services/haAiAgentApi.ts`
- Added `API_KEY` import from environment variables
- Added `withAuthHeaders()` function to add authentication headers
- Updated `fetchJSON()` to use authentication headers on all requests

**Changes:**
```typescript
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const authHeaders: Record<string, string> = {
    'Authorization': `Bearer ${API_KEY}`,
    'X-HomeIQ-API-Key': API_KEY,
  };
  // ... implementation
}
```

### 2. Updated `services/ai-automation-ui/nginx.conf`
- Added specific location block for `/api/ha-ai-agent/(.*)` routes
- Routes requests to `ha-ai-agent-service:8030`
- Forwards authentication headers (`X-HomeIQ-API-Key` and `Authorization`)
- Added CORS headers to allow `X-HomeIQ-API-Key` header

**New Location Block:**
```nginx
# API proxy to ha-ai-agent-service (HA AI Agent - Epic AI-20)
location ~* ^/api/ha-ai-agent/(.*) {
    resolver 127.0.0.11 valid=30s;
    resolver_timeout 5s;

    set $backend http://ha-ai-agent-service:8030;
    proxy_pass $backend/api/$1;

    # Forward authentication headers
    proxy_set_header Authorization $http_authorization;
    proxy_set_header X-HomeIQ-API-Key $http_x_homeiq_api_key;
    proxy_pass_request_headers on;
    
    # ... rest of configuration
}
```

## Service Status

**Note:** The `ha-ai-agent-service` currently does NOT require authentication (per security documentation). However, the frontend now sends authentication headers for consistency and future-proofing. If the service adds authentication in the future, it will work without code changes.

## Testing

After rebuilding and restarting:
1. Navigate to the AGENT page: http://localhost:3001/ha-agent
2. The "Missing X-HomeIQ-API-Key" error should be gone
3. Try sending a message - it should work without authentication errors

## Files Modified

1. `services/ai-automation-ui/src/services/haAiAgentApi.ts` - Added authentication headers
2. `services/ai-automation-ui/nginx.conf` - Added ha-ai-agent proxy configuration

