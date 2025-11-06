# Rate Limit Fix Implementation Plan

**Date:** November 6, 2025  
**Target:** Priority 1 Critical Fixes  
**Context7 Best Practices:** Applied throughout

---

## Overview

Fix critical rate limiting issues causing 429 errors and daily batch failures. Three Priority 1 fixes will be implemented following Context7 best practices.

---

## Task 1: Fix Priority Score Calculation Bug

### Problem
`calculate_synergy_priority_score()` uses `.get()` method on SQLAlchemy objects, which don't have this method. This causes `AttributeError` and breaks daily batch synergy suggestion generation.

### Solution
Create a helper function that safely handles both dict and SQLAlchemy objects using `getattr()` and proper type checking.

### Context7 Best Practices
- ✅ Type-safe attribute access
- ✅ Proper error handling
- ✅ Clear helper function with docstring
- ✅ Backward compatible (handles both types)

### Implementation
**File:** `services/ai-automation-service/src/database/crud.py`  
**Lines:** 1162-1166

**Code:**
```python
def _get_attr_safe(obj: Union[Dict, Any], attr: str, default: Any) -> Any:
    """
    Safely get attribute from dict or object.
    
    Context7 Best Practice: Type-safe attribute access that handles
    both dict and SQLAlchemy objects without raising exceptions.
    
    Args:
        obj: Dictionary or object instance
        attr: Attribute name
        default: Default value if attribute not found
    
    Returns:
        Attribute value or default
    """
    if isinstance(obj, dict):
        return obj.get(attr, default)
    else:
        return getattr(obj, attr, default)
```

**Replace lines 1162-1166 with:**
```python
# Extract values safely (works with both dict and object)
impact_score = float(_get_attr_safe(synergy, 'impact_score', 0.5))
confidence = float(_get_attr_safe(synergy, 'confidence', 0.7))
pattern_support_score = float(_get_attr_safe(synergy, 'pattern_support_score', 0.0))
validated_by_patterns = bool(_get_attr_safe(synergy, 'validated_by_patterns', False))
complexity = str(_get_attr_safe(synergy, 'complexity', 'medium')).lower()
```

**Add import if needed:**
```python
from typing import Union, Any, Dict
```

---

## Task 2: Exempt Health/Status Endpoints from Rate Limiting

### Problem
Health check and status endpoints are being rate-limited, causing false 429 errors. These endpoints should not count against rate limits as they're used for monitoring.

### Solution
Skip rate limiting for specific endpoint paths that are used for health checks and status monitoring.

### Context7 Best Practices
- ✅ Early return pattern (performance)
- ✅ Clear exemption list (maintainability)
- ✅ Configurable exemptions (flexibility)

### Implementation
**File:** `services/ai-automation-service/src/api/middlewares.py`  
**Lines:** 134-152 (in `dispatch` method)

**Add at start of `dispatch` method:**
```python
async def dispatch(self, request: Request, call_next: Callable):
    # Exempt health checks and status endpoints from rate limiting
    # Context7 Best Practice: Early return for exempt paths (performance)
    exempt_paths = [
        '/health',
        '/api/health',
        '/api/analysis/status',
        '/api/analysis/schedule'
    ]
    
    if any(request.url.path.startswith(path) for path in exempt_paths):
        # Process request without rate limiting
        return await call_next(request)
    
    # ... rest of existing rate limiting logic
```

---

## Task 3: Increase Rate Limits for Internal Traffic

### Problem
Dashboard and other internal services (Docker network 172.x.x.x) are hitting rate limits because they use the same limits as external API consumers. Internal traffic should have higher limits.

### Solution
Detect internal network IPs and apply higher rate limits. Internal traffic gets 2000 requests/minute vs 600 for external.

### Context7 Best Practices
- ✅ Configuration-based limits (maintainability)
- ✅ Clear separation of concerns
- ✅ Proper IP detection logic

### Implementation
**File:** `services/ai-automation-service/src/api/middlewares.py`

**Option 1: In `__init__` method (add configurable internal limits):**
```python
def __init__(
    self,
    app,
    requests_per_minute: int = 600,
    requests_per_hour: int = 10000,
    internal_requests_per_minute: int = 2000,  # NEW: Higher limit for internal
    key_header: str = "X-User-ID"
):
    super().__init__(app)
    self.requests_per_minute = requests_per_minute
    self.internal_requests_per_minute = internal_requests_per_minute  # NEW
    self.requests_per_hour = requests_per_hour
    self.key_header = key_header
    # Internal network prefixes (Docker, private networks)
    self.internal_network_prefixes = ['172.', '10.', '192.168.', '127.0.0.1']
    # Calculate refill rate
    self.refill_rate = requests_per_minute / 60.0
    self.internal_refill_rate = internal_requests_per_minute / 60.0  # NEW
    # Set capacity
    self.bucket_capacity = requests_per_minute
    self.internal_bucket_capacity = internal_requests_per_minute  # NEW
```

**Option 2: In `dispatch` method (detect internal and use appropriate limits):**
```python
async def dispatch(self, request: Request, call_next: Callable):
    # ... exempt paths check (from Task 2) ...
    
    # Get identifier
    identifier = request.headers.get(self.key_header)
    if not identifier:
        identifier = request.client.host if request.client else "unknown"
    
    # Detect internal traffic (Context7: Clear separation of concerns)
    is_internal = any(identifier.startswith(prefix) for prefix in self.internal_network_prefixes)
    
    # Use appropriate limits based on traffic type
    if is_internal:
        effective_limit = self.internal_requests_per_minute
        effective_refill = self.internal_refill_rate
        effective_capacity = self.internal_bucket_capacity
    else:
        effective_limit = self.requests_per_minute
        effective_refill = self.refill_rate
        effective_capacity = self.bucket_capacity
    
    # Check rate limit with appropriate bucket
    if not self._check_rate_limit(identifier, effective_refill, effective_capacity):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {effective_limit}/min"
            },
            headers={"Retry-After": "60"}
        )
    
    # ... rest of method
```

**Update `_check_rate_limit` to accept parameters:**
```python
def _check_rate_limit(
    self, 
    identifier: str, 
    refill_rate: float = None,
    capacity: int = None
) -> bool:
    """Check if request is within rate limit"""
    bucket = _rate_limit_buckets[identifier]
    current_time = time.time()
    
    # Use provided refill_rate and capacity, or defaults
    effective_refill_rate = refill_rate if refill_rate is not None else self.refill_rate
    effective_capacity = capacity if capacity is not None else self.bucket_capacity
    
    # Initialize bucket with correct capacity and refill rate if not set
    if "capacity" not in bucket or bucket.get("capacity") != effective_capacity:
        bucket["capacity"] = effective_capacity
        bucket["tokens"] = min(bucket.get("tokens", effective_capacity), effective_capacity)
    
    if "refill_rate" not in bucket or bucket.get("refill_rate") != effective_refill_rate:
        bucket["refill_rate"] = effective_refill_rate
    
    # Refill tokens
    time_since_refill = current_time - bucket["last_refill"]
    tokens_to_add = time_since_refill * bucket["refill_rate"]
    bucket["tokens"] = min(
        bucket["capacity"],
        bucket["tokens"] + tokens_to_add
    )
    bucket["last_refill"] = current_time
    
    # Check if tokens available
    if bucket["tokens"] >= 1.0:
        bucket["tokens"] -= 1.0
        return True
    else:
        logger.warning(f"Rate limit exceeded for {identifier}")
        return False
```

---

## Testing Strategy

### Unit Tests
1. Test `_get_attr_safe` with dict and SQLAlchemy objects
2. Test rate limit exemption for health endpoints
3. Test internal vs external rate limit detection

### Integration Tests
1. Verify daily batch completes without errors
2. Verify health endpoints return 200 (not 429)
3. Verify dashboard can poll at reasonable frequency

### Manual Testing
1. Poll `/api/patterns/list` rapidly - should work for internal IPs
2. Check daily batch logs - no AttributeError
3. Verify health endpoints are accessible

---

## Files to Modify

1. `services/ai-automation-service/src/database/crud.py`
   - Add `_get_attr_safe` helper function
   - Fix `calculate_synergy_priority_score` to use helper

2. `services/ai-automation-service/src/api/middlewares.py`
   - Add exempt paths check in `dispatch`
   - Add internal network detection
   - Update `__init__` with internal limits
   - Update `_check_rate_limit` to accept parameters

---

## Success Criteria

- ✅ Daily batch completes without AttributeError
- ✅ Health endpoints return 200 (not 429)
- ✅ Dashboard can poll at 1-2 second intervals
- ✅ External API consumers still limited to 600/min
- ✅ All changes backward compatible

---

## Context7 Compliance Checklist

- ✅ Type hints on all functions
- ✅ Proper error handling (no exceptions raised)
- ✅ Clear documentation (docstrings)
- ✅ Backward compatible changes
- ✅ Performance optimized (early returns)
- ✅ Maintainable code (clear separation of concerns)

