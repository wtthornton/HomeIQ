# Health Dashboard API Configuration Guide

## Overview

The health dashboard requires proper configuration of API clients to connect to backend services. This guide documents the correct configuration to prevent common routing issues.

## API Client Architecture

The health dashboard uses **two separate API clients** with different purposes:

### 1. AdminApiClient (System Monitoring)
- **Service**: `admin-api` (port 8003)
- **Purpose**: System health, statistics, Docker management
- **Base URL**: `http://localhost:8003`
- **Environment Variable**: `VITE_API_BASE_URL`

**Endpoints:**
- `/api/health` - Basic health check
- `/api/v1/health` - Enhanced health with dependencies
- `/api/v1/stats` - Statistics
- `/api/v1/docker/containers` - Container management
- `/api/v1/alerts/active` - Active alerts

### 2. DataApiClient (Feature Data)
- **Service**: `data-api` (port 8006)
- **Purpose**: Devices, entities, events, sports, analytics
- **Base URL**: `http://localhost:8006`
- **Environment Variable**: `VITE_DATA_API_URL`

**Endpoints:**
- `/api/devices` - Device registry
- `/api/entities` - Entity registry
- `/api/integrations` - Integration registry
- `/api/v1/events` - Event queries
- `/api/v1/sports/games/live` - Sports data
- `/api/v1/energy/*` - Energy correlation data

## Configuration

### Docker Compose Configuration

```yaml
health-dashboard:
  environment:
    - VITE_API_BASE_URL=http://localhost:8003  # Admin API
    - VITE_DATA_API_URL=http://localhost:8006   # Data API (CRITICAL)
    - VITE_WS_URL=ws://localhost:8001/ws
    - VITE_ENVIRONMENT=production
```

### Code Configuration

The API clients are configured in `services/health-dashboard/src/services/api.ts`:

```typescript
// Admin API Client - System Monitoring
class AdminApiClient extends BaseApiClient {
  constructor() {
    super(ADMIN_API_BASE_URL);  // Uses VITE_API_BASE_URL
  }
}

// Data API Client - Feature Data Hub  
class DataApiClient extends BaseApiClient {
  constructor() {
    // Use data-api URL (port 8006) which has the /api/devices endpoint
    const DATA_API_URL = import.meta.env.VITE_DATA_API_URL || 'http://localhost:8006';
    super(DATA_API_URL);
  }
}
```

## Common Issues & Solutions

### Issue: Dashboard Shows "0 Devices"

**Symptom**: Dashboard displays 0 devices when devices exist in Home Assistant

**Root Cause**: `DataApiClient` not configured with correct base URL, causing it to make requests to the dashboard's origin instead of the API service

**Solution**: 
1. Ensure `VITE_DATA_API_URL=http://localhost:8006` is set in `docker-compose.yml`
2. Rebuild the dashboard: `docker-compose up -d --build health-dashboard`
3. Verify: `curl http://localhost:8006/api/devices?limit=5`

**Verification**:
```bash
# Check if data-api is responding
curl http://localhost:8006/api/devices?limit=5

# Check if dashboard can reach data-api
curl http://localhost:3000/api/devices?limit=5

# Check docker-compose environment
docker exec homeiq-dashboard env | grep VITE
```

### Issue: 502 Bad Gateway Errors

**Symptom**: Dashboard shows 502 errors when loading devices/entities

**Root Cause**: Dashboard's nginx is trying to proxy to a non-existent service

**Solution**:
1. Verify `data-api` container is running: `docker ps | grep data-api`
2. Verify port mapping: Container `homeiq-data-api` should expose port 8006
3. Check logs: `docker logs homeiq-data-api --tail 50`

### Issue: CORS Errors in Browser Console

**Symptom**: Browser shows CORS errors when making API requests

**Root Cause**: Data API not configured to allow requests from dashboard origin

**Solution**: Add CORS configuration to data-api:
```python
# In services/data-api/src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing the Configuration

### Verify Admin API Connection
```bash
curl http://localhost:8003/api/health
# Should return: {"status": "healthy", ...}
```

### Verify Data API Connection
```bash
curl http://localhost:8006/api/devices?limit=5
# Should return: {"devices": [...], "count": 5, "limit": 5}
```

### Verify Dashboard Can Reach APIs
```bash
# Check environment variables in dashboard container
docker exec homeiq-dashboard env | grep VITE

# Should show:
# VITE_API_BASE_URL=http://localhost:8003
# VITE_DATA_API_URL=http://localhost:8006
```

## Architecture Notes

### Why Two Separate Clients?

1. **Separation of Concerns**
   - Admin API: System administration, container management
   - Data API: Feature data (devices, events, sports)

2. **Scalability**
   - Services can be scaled independently
   - Different caching strategies per service
   - Isolated failure domains

3. **Security**
   - Different authentication requirements
   - Admin API requires elevated privileges
   - Data API is read-mostly

### Service Ports Reference

| Service | Container Port | Host Port | Purpose |
|---------|---------------|-----------|---------|
| health-dashboard | 80 | 3000 | Web UI |
| admin-api | 8004 | 8003 | System admin |
| data-api | 8006 | 8006 | Feature data |
| websocket-ingestion | 8001 | 8001 | Event ingestion |
| influxdb | 8086 | 8086 | Time-series DB |

## Environment Variables Summary

### Dashboard Environment Variables

```bash
VITE_API_BASE_URL=http://localhost:8003    # Admin API (system monitoring)
VITE_DATA_API_URL=http://localhost:8006    # Data API (feature data)
VITE_WS_URL=ws://localhost:8001/ws         # WebSocket connection
VITE_ENVIRONMENT=production                 # Environment mode
```

### Critical Rule: Never Use Empty Base URL

**❌ WRONG:**
```typescript
super('');  // Causes requests to go to dashboard origin
```

**✅ CORRECT:**
```typescript
super('http://localhost:8006');  // Explicit service URL
// Or
super(DATA_API_URL);  // From environment variable
```

## Quick Reference Checklist

When dashboard shows 0 devices or 502 errors:

1. ✅ Check `VITE_DATA_API_URL` is set in `docker-compose.yml`
2. ✅ Verify `data-api` container is running: `docker ps | grep data-api`
3. ✅ Test API directly: `curl http://localhost:8006/api/devices?limit=5`
4. ✅ Check dashboard logs: `docker logs homeiq-dashboard --tail 50`
5. ✅ Rebuild dashboard if config changed: `docker-compose up -d --build health-dashboard`

## Maintenance

### When Adding New API Endpoints

1. **Determine correct service**: Admin API vs Data API
2. **Add to correct client class** in `services/health-dashboard/src/services/api.ts`
3. **Update this documentation** with endpoint details
4. **Add environment variable** to `docker-compose.yml` if needed
5. **Test end-to-end** to ensure dashboard can reach the endpoint

### When Changing Service Ports

1. **Update `docker-compose.yml`** with new port mapping
2. **Update environment variables** in dashboard service
3. **Rebuild affected containers**
4. **Update this documentation** with new ports

