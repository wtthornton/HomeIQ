# API Endpoint Standardization Guide

**Date:** October 20, 2025  
**Purpose:** Prevent API endpoint confusion and ensure consistent documentation  
**Status:** ✅ **IMPLEMENTED**

## The Problem We Solved

**Issue:** Conflicting API endpoint documentation caused frontend to call wrong URLs
- **Documentation said:** `/health/services` 
- **Actual endpoint:** `/api/v1/health/services`
- **Result:** 404 errors, UI showing pause icons instead of healthy status

## Root Cause Analysis

### 1. Router Mounting Confusion
```python
# services/admin-api/src/main.py (line 291-294)
self.app.include_router(
    self.health_endpoints.router,  # Defines /health/services
    prefix="/api/v1",              # Mounts at /api/v1
    tags=["Health"]
)
# Final endpoint: /api/v1/health/services
```

### 2. Documentation Inconsistency
- **Some docs:** Referenced `/health/services` (wrong)
- **Some docs:** Referenced `/api/v1/health/services` (correct)
- **Frontend code:** Used wrong endpoint

## Correct API Endpoints

### Admin API (Port 8003)
| Service | Endpoint | Purpose |
|---------|----------|---------|
| **Health Services** | `GET /api/v1/health/services` | All services health status |
| **Health Dependencies** | `GET /api/v1/health/dependencies` | Dependency health |
| **Health Metrics** | `GET /api/v1/health/metrics` | Health metrics |
| **Statistics** | `GET /api/v1/stats` | Service statistics |
| **Services Stats** | `GET /api/v1/stats/services` | Individual service stats |

### Data API (Port 8006)
| Service | Endpoint | Purpose |
|---------|----------|---------|
| **Events** | `GET /api/v1/events` | Event queries |
| **Devices** | `GET /api/v1/devices` | Device information |
| **Sports** | `GET /api/v1/sports/games/history` | Sports data |

## Documentation Standards

### ✅ Correct Format
```markdown
**Endpoint:** `GET /api/v1/health/services`
**Purpose:** Get health status for all external data sources
**Response:** `{"weather-api": {"status": "healthy"}, ...}`
```

### ❌ Incorrect Format
```markdown
**Endpoint:** `GET /health/services`  # Missing /api/v1 prefix
**Endpoint:** `/health/services`      # Missing GET method
```

## Files Updated

### 1. Frontend Code ✅
**File:** `services/health-dashboard/src/services/api.ts`
- **Line 116:** Fixed endpoint URL
- **Status:** ✅ Applied and working

### 2. Implementation Documentation ✅
**Files Updated:**
- `implementation/analysis/HA_EVENT_CALL_TREE.md`
- `implementation/DATA_SOURCES_FIX_SUCCESS_REPORT.md`
- `implementation/DATA_SOURCES_DIAGNOSTIC_REPORT.md`
- `implementation/DATA_SOURCES_FIX_IMPLEMENTATION_PLAN.md`

**Changes:** All references updated to `/api/v1/health/services`

### 3. API Reference Documentation ✅
**Files Already Correct:**
- `docs/API_COMPREHENSIVE_REFERENCE.md`
- `docs/SERVICES_OVERVIEW.md`

## Prevention Measures

### 1. API Endpoint Testing
```bash
# Always test endpoints before documenting
curl http://localhost:8003/api/v1/health/services
# Should return 200 OK with JSON data
```

### 2. Documentation Review Process
- **Before documenting:** Test the actual endpoint
- **When updating:** Verify all references are consistent
- **Code changes:** Update documentation immediately

### 3. Frontend Integration Tests
```typescript
// Add integration tests for API endpoints
describe('Data Sources API', () => {
  it('should fetch services health', async () => {
    const response = await fetch('/api/v1/health/services');
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('weather-api');
  });
});
```

## Quick Reference

### How to Find Correct Endpoints
1. **Check router mounting:** Look for `include_router(..., prefix="/api/v1")`
2. **Test the endpoint:** Use curl to verify it works
3. **Check existing code:** Look at working API calls
4. **Document immediately:** Update docs when endpoints change

### Common Patterns
```python
# Router definition
@router.get("/health/services")  # Relative path

# Router mounting  
app.include_router(router, prefix="/api/v1")  # Mount point

# Final endpoint
GET /api/v1/health/services  # Absolute path
```

## Verification Commands

### Test All Health Endpoints
```bash
# Admin API Health Endpoints
curl http://localhost:8003/api/v1/health/services
curl http://localhost:8003/api/v1/health/dependencies  
curl http://localhost:8003/api/v1/health/metrics

# Data API Endpoints
curl http://localhost:8006/api/v1/events
curl http://localhost:8006/api/v1/devices
```

### Expected Responses
- **200 OK:** Endpoint exists and working
- **404 Not Found:** Wrong endpoint URL
- **500 Internal Error:** Service issue (not endpoint issue)

## Summary

**Problem:** API endpoint documentation inconsistency
**Solution:** Standardized all references to `/api/v1/health/services`
**Prevention:** Added testing requirements and review process
**Status:** ✅ All documentation updated and consistent

**Key Takeaway:** Always test endpoints before documenting them. The router mounting prefix is critical for determining the correct absolute endpoint URL.

This standardization prevents future confusion and ensures the frontend always calls the correct API endpoints! 🎉

