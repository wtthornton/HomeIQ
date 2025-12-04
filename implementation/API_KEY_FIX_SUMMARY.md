# API Key Authentication Fix

## Issue
The frontend was showing "Missing X-HomeIQ-API-Key or Authorization header" errors because:
1. The backend service expects `AI_AUTOMATION_API_KEY` environment variable
2. The docker-compose.yml was not mapping `API_KEY` from `.env` to `AI_AUTOMATION_API_KEY`
3. The nginx proxy was not forwarding the `X-HomeIQ-API-Key` header to the backend

## Fixes Applied

### 1. Docker Compose Configuration (`docker-compose.yml`)
Added explicit mapping of `API_KEY` to `AI_AUTOMATION_API_KEY`:
```yaml
- AI_AUTOMATION_API_KEY=${API_KEY:-hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR}
- AI_AUTOMATION_ADMIN_API_KEY=${API_KEY:-hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR}
```

### 2. Nginx Configuration (`services/ai-automation-ui/nginx.conf`)
Added header forwarding for authentication:
```nginx
# Forward authentication headers
proxy_set_header Authorization $http_authorization;
proxy_set_header X-HomeIQ-API-Key $http_x_homeiq_api_key;
proxy_pass_request_headers on;
```

Also updated CORS headers to allow `X-HomeIQ-API-Key`:
```nginx
add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-HomeIQ-API-Key' always;
```

## Required Actions

### 1. Verify .env File
Ensure your `.env` file contains:
```bash
API_KEY=your-actual-api-key-here
```

If you don't have an API key set, the default fallback `hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR` will be used.

### 2. Rebuild Frontend Container
Since Vite bundles environment variables at build time, you need to rebuild the frontend container:

```bash
docker compose build ai-automation-ui
docker compose up -d ai-automation-ui
```

Or rebuild all services:
```bash
docker compose build
docker compose up -d
```

### 3. Restart Backend Service
Restart the ai-automation-service to pick up the new environment variable mapping:

```bash
docker compose restart ai-automation-service
```

## Verification

After applying the fixes:

1. **Check backend logs** to ensure it started with the API key:
   ```bash
   docker compose logs ai-automation-service | grep -i "authentication"
   ```
   Should show: `✅ Authentication middleware enabled (mandatory)`

2. **Test the frontend** - The error "Missing X-HomeIQ-API-Key or Authorization header" should be gone

3. **Check browser console** - No authentication errors should appear

## Architecture Notes

- **Frontend**: Reads `VITE_API_KEY` from build-time environment (via docker-compose build args)
- **Backend**: Reads `AI_AUTOMATION_API_KEY` from runtime environment (via docker-compose environment section)
- **Nginx**: Forwards `X-HomeIQ-API-Key` header from frontend requests to backend
- **Authentication**: Backend middleware validates the header against the configured API key

## Related Files

- `docker-compose.yml` - Service configuration and environment variable mapping
- `services/ai-automation-ui/nginx.conf` - Nginx proxy configuration
- `services/ai-automation-service/src/api/middlewares.py` - Authentication middleware
- `services/ai-automation-service/src/config.py` - Configuration settings
- `.env` - Environment variables (user-specific, not in git)

