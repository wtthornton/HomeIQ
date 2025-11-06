# Rate Limit Analysis and Recommendations

**Date:** November 6, 2025  
**Issue:** API rate limiting causing 429 errors  
**Source:** Health dashboard polling `/api/patterns/list` at high frequency

---

## Problem Summary

### Issue 1: API Rate Limiting (HTTP 429 Errors)
- **Symptom:** Health dashboard is receiving `429 Too Many Requests` errors
- **Root Cause:** Dashboard is polling `/api/patterns/list` at high frequency, exceeding the 600 requests/minute limit per IP
- **Impact:** Dashboard cannot display pattern data, user experience degraded

### Issue 2: Bug in Priority Score Calculation
- **Symptom:** `AttributeError: 'SynergyOpportunity' object has no attribute 'get'`
- **Root Cause:** Code tries to use `.get()` on SQLAlchemy object (dict method)
- **Impact:** Daily batch synergy suggestion generation fails

---

## Current Rate Limiting Configuration

### Settings (from `middlewares.py`)
- **Requests per minute:** 600
- **Requests per hour:** 10,000
- **Refill rate:** 10 tokens/second
- **Bucket capacity:** 600 tokens (1 minute burst)
- **Per-IP tracking:** Yes (fallback when no X-User-ID header)

### Problem Analysis
1. **High-frequency polling:** Dashboard likely polling every 1-2 seconds
   - At 2 seconds: 30 requests/minute per endpoint
   - Multiple endpoints: `/api/patterns/list`, `/api/analysis/status`, `/api/analysis/schedule`
   - Total: ~90-150 requests/minute just for dashboard updates
   
2. **All requests from same IP:** 172.18.0.22 (dashboard container)
   - All dashboard requests count against single IP bucket
   - No differentiation between internal/external traffic

3. **No endpoint exemptions:** Health checks and read-only endpoints are rate-limited the same as write operations

---

## Recommendations

### Priority 1: Immediate Fixes (Critical)

#### 1. Fix Priority Score Calculation Bug
**File:** `services/ai-automation-service/src/database/crud.py`

**Problem:** Line 1162-1166 tries to use `.get()` on SQLAlchemy object
```python
# CURRENT (BROKEN)
impact_score = float(getattr(synergy, 'impact_score', synergy.get('impact_score', 0.5)))
```

**Fix:** Handle both dict and object properly
```python
# FIXED
def _get_attr_safe(obj, attr, default):
    """Safely get attribute from dict or object"""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    else:
        return getattr(obj, attr, default)

impact_score = float(_get_attr_safe(synergy, 'impact_score', 0.5))
confidence = float(_get_attr_safe(synergy, 'confidence', 0.7))
pattern_support_score = float(_get_attr_safe(synergy, 'pattern_support_score', 0.0))
validated_by_patterns = bool(_get_attr_safe(synergy, 'validated_by_patterns', False))
complexity = str(_get_attr_safe(synergy, 'complexity', 'medium')).lower()
```

#### 2. Exempt Health/Status Endpoints from Rate Limiting
**File:** `services/ai-automation-service/src/api/middlewares.py`

**Change:** Skip rate limiting for health checks and status endpoints
```python
async def dispatch(self, request: Request, call_next: Callable):
    # Exempt health checks and status endpoints
    exempt_paths = ['/health', '/api/health', '/api/analysis/status', '/api/analysis/schedule']
    if any(request.url.path.startswith(path) for path in exempt_paths):
        return await call_next(request)
    
    # ... rest of rate limiting logic
```

#### 3. Increase Rate Limits for Internal Traffic
**Option A:** Detect internal network IPs (Docker network: 172.x.x.x)
```python
# In RateLimitMiddleware.__init__
self.internal_network_prefixes = ['172.', '10.', '192.168.']

# In dispatch
is_internal = any(identifier.startswith(prefix) for prefix in self.internal_network_prefixes)
if is_internal:
    # Use higher limits for internal traffic
    requests_per_minute = 2000  # 10x increase for internal
else:
    requests_per_minute = 600
```

**Option B:** Use X-Forwarded-For header to identify dashboard traffic
```python
# Check for dashboard user agent or custom header
dashboard_header = request.headers.get('X-Source', '')
if dashboard_header == 'dashboard':
    # Higher limits for dashboard
    requests_per_minute = 2000
```

### Priority 2: Short-Term Improvements

#### 4. Add Endpoint-Specific Rate Limits
**Different limits for different endpoint types:**
- **Read-only endpoints:** Higher limits (1000/min)
- **Write endpoints:** Lower limits (100/min)
- **Health/Status:** No limits

#### 5. Implement Response Caching
**File:** Add caching middleware or endpoint-level caching

**Benefits:**
- Reduce database queries
- Reduce API calls from frontend
- Faster response times

**Implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache patterns list for 5 seconds
@lru_cache(maxsize=1)
def get_cached_patterns():
    # Cache with TTL
    pass
```

#### 6. Add Request Deduplication
**Prevent duplicate simultaneous requests:**
- Track in-flight requests by path + params
- Return same response for duplicate requests
- Reduces load when dashboard polls rapidly

### Priority 3: Long-Term Solutions

#### 7. Implement WebSocket for Real-Time Updates
**Replace polling with WebSocket:**
- Dashboard subscribes to pattern updates
- Server pushes updates when data changes
- Eliminates polling overhead

#### 8. Use Redis for Distributed Rate Limiting
**Current:** In-memory rate limiting (single instance)
**Better:** Redis-based rate limiting
- Works across multiple instances
- Persistent rate limit state
- Better for production scaling

#### 9. Add Rate Limit Metrics and Monitoring
**Track rate limit hits:**
- Log rate limit violations
- Monitor which endpoints/IPs hit limits most
- Alert on excessive rate limiting

---

## Implementation Plan

### Phase 1: Critical Fixes (Today)
1. ✅ Fix `calculate_synergy_priority_score` bug
2. ✅ Exempt health/status endpoints from rate limiting
3. ✅ Increase limits for internal traffic (172.x.x.x)

### Phase 2: Short-Term (This Week)
4. Add endpoint-specific rate limits
5. Implement response caching for `/api/patterns/list`
6. Add request deduplication

### Phase 3: Long-Term (Next Sprint)
7. Implement WebSocket for real-time updates
8. Migrate to Redis-based rate limiting
9. Add rate limit monitoring and alerts

---

## Code Changes Required

### File 1: `services/ai-automation-service/src/database/crud.py`
**Lines:** 1162-1166

**Change:** Fix attribute access for SQLAlchemy objects

### File 2: `services/ai-automation-service/src/api/middlewares.py`
**Lines:** 134-152

**Changes:**
1. Add exempt paths list
2. Add internal network detection
3. Add endpoint-specific limits

### File 3: `services/ai-automation-service/src/config.py`
**Add:**
```python
# Rate Limiting Configuration
rate_limit_requests_per_minute: int = 600
rate_limit_internal_requests_per_minute: int = 2000
rate_limit_health_exempt: bool = True
```

---

## Expected Impact

### After Phase 1 Fixes
- ✅ No more 429 errors for health/status endpoints
- ✅ Dashboard can poll at reasonable frequency
- ✅ Daily batch no longer crashes on synergy suggestions

### After Phase 2 Improvements
- 📉 50-70% reduction in API calls (caching)
- 📈 Better response times
- 📊 Reduced database load

### After Phase 3 Solutions
- 🚀 Real-time updates (no polling)
- 📈 Scalable rate limiting
- 🔍 Better observability

---

## Testing Recommendations

1. **Load Testing:** Simulate dashboard polling patterns
2. **Rate Limit Testing:** Verify exempt endpoints work
3. **Bug Fix Testing:** Test priority score calculation with SQLAlchemy objects
4. **Integration Testing:** Verify daily batch completes successfully

---

## Monitoring

### Metrics to Track
- Rate limit violations per endpoint
- Average requests per minute per IP
- Cache hit rates (when implemented)
- Response times by endpoint

### Alerts
- Alert when rate limit violations exceed threshold
- Alert when specific IP hits limits repeatedly
- Alert when cache hit rate drops below 50%

---

## Notes

- Current rate limit of 600/min is reasonable for external API consumers
- Dashboard polling is the main issue (internal traffic should have higher limits)
- Priority score bug is blocking daily batch from completing
- All fixes are backward compatible

