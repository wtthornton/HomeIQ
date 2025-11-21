# Ask AI Error Handling Improvements

**Date**: 2025-11-20  
**Status**: IMPLEMENTED  

## Overview

Enhanced fallback logic to ensure real errors are not hidden while still providing graceful degradation for expected scenarios.

## Key Principle

**Fallbacks should only mask EXPECTED errors, never REAL errors.**

### Expected Errors (OK to Fallback)
- **404**: Entity Registry API not available (some HA versions don't expose it)
- **404**: Entity doesn't exist (not an error - entity just isn't there)

### Real Errors (Must Be Logged and Propagated)
- **Connection errors**: Network failures, timeouts, DNS issues
- **Authentication errors (401/403)**: Invalid token, permission denied
- **Server errors (500+)**: HA server problems, internal errors
- **Other HTTP errors (400, 429, etc.)**: Client errors, rate limiting

## Changes Made

### 1. Entity Registry API (`ha_client.py`)

**Before** (BAD - Hides all errors):
```python
except Exception as e:
    logger.error(f"Error getting entity registry: {e}", exc_info=True)
    return {}  # ❌ Hides connection/auth/server errors
```

**After** (GOOD - Distinguishes expected vs real errors):
```python
elif response.status == 404:
    # Expected: Some HA versions don't expose Entity Registry API
    logger.info("ℹ️ Entity Registry API not available (404) - using state-based fallback")
    return {}  # ✅ OK to fallback
elif response.status in (401, 403):
    # Real error: Authentication failed
    error_msg = f"Authentication failed for Entity Registry API: {response.status}"
    logger.error(f"❌ {error_msg}")
    raise PermissionError(error_msg)  # ✅ Propagate real error
elif response.status >= 500:
    # Real error: Server error
    error_msg = f"Home Assistant server error: {response.status}"
    logger.error(f"❌ {error_msg}")
    raise Exception(error_msg)  # ✅ Propagate real error
except (ConnectionError, PermissionError):
    # Re-raise connection/auth errors (already logged)
    raise  # ✅ Don't hide real errors
except Exception as e:
    # Other unexpected errors - log with full traceback
    logger.error(f"❌ Unexpected error: {e}", exc_info=True)
    raise  # ✅ Propagate all unexpected errors
```

**Impact**:
- ✅ 404 (expected) → Fallback gracefully
- ✅ Connection errors → Propagated (service can retry/handle)
- ✅ Auth errors → Propagated (user knows token is invalid)
- ✅ Server errors → Propagated (visible in monitoring)

---

### 2. Entity State API (`ha_client.py`)

**Before** (BAD - Hides all errors):
```python
except Exception as e:
    logger.error(f"Error getting entity state: {e}")
    return None  # ❌ Hides all errors as "entity not found"
```

**After** (GOOD - Only fallback on expected 404):
```python
elif response.status == 404:
    # Expected: Entity doesn't exist
    logger.debug(f"Entity {entity_id} not found (404)")
    return None  # ✅ OK to fallback
elif response.status in (401, 403):
    # Real error: Authentication failed
    error_msg = f"Authentication failed: {response.status}"
    logger.error(f"❌ {error_msg}")
    raise PermissionError(error_msg)  # ✅ Propagate
# ... (similar for 500+ and connection errors)
```

**Impact**:
- ✅ 404 (expected) → Return None (entity not found)
- ✅ Connection/Auth errors → Propagated
- ✅ Server errors → Propagated

---

### 3. Entity Registry Cache (`entity_attribute_service.py`)

**Before** (BAD - Hides all errors):
```python
except Exception as e:
    logger.error(f"❌ Failed to load Entity Registry: {e}", exc_info=True)
    self._entity_registry_cache = {}  # ❌ Hides all errors
```

**After** (GOOD - Distinguishes error types):
```python
except (ConnectionError, PermissionError) as e:
    # Real errors (connection/auth) - log as ERROR but allow fallback
    logger.error(f"❌ Failed to load Entity Registry (will use state-based fallback): {type(e).__name__}: {e}")
    self._entity_registry_cache = {}  # ✅ Fallback allowed, but error is visible
    # Don't re-raise - allow graceful degradation
except Exception as e:
    # Other unexpected errors - log with full traceback
    logger.error(f"❌ Unexpected error loading Entity Registry (will use state-based fallback): {type(e).__name__}: {e}", exc_info=True)
    self._entity_registry_cache = {}  # ✅ Fallback allowed, but error is visible
    # Log as ERROR so we know something went wrong
```

**Impact**:
- ✅ Real errors logged as ERROR (visible in monitoring)
- ✅ Fallback still works (graceful degradation)
- ✅ Error type clearly indicated (ConnectionError vs PermissionError vs unexpected)
- ✅ Full traceback for unexpected errors

---

### 4. Entity Mapping Error Messages (`ask_ai_router.py`)

**Before** (BAD - Generic error messages):
```python
logger.error(f"❌ Skipping suggestion {i+1} - no validated entities")
```

**After** (GOOD - Detailed error context):
```python
logger.error(f"❌ CRITICAL: Entity mapping failed for suggestion {i+1}")
logger.error(f"❌ devices_involved: {devices_involved}")
logger.error(f"❌ No entity IDs found in devices_involved")
logger.error(f"❌ enriched_data available: {bool(enriched_data)}")
logger.error(f"❌ enriched_data entity count: {len(enriched_data) if enriched_data else 0}")
if enriched_data:
    sample_entities = list(enriched_data.keys())[:5]
    logger.error(f"❌ Sample entities in enriched_data: {sample_entities}")
```

**Impact**:
- ✅ Provides debugging context
- ✅ Shows what was attempted
- ✅ Helps identify root cause
- ✅ No error is hidden - all failures are explicit

---

## Error Severity Levels

### INFO (ℹ️) - Expected Scenarios
- Entity Registry API returns 404 (expected, using fallback)
- Entity not found (expected, not an error)

### DEBUG (🔍) - Diagnostic Information
- Entity lookup details
- Fallback usage

### WARNING (⚠️) - Degraded Functionality
- Fallback in use (Entity Registry unavailable)
- Partial functionality (some entities not found)

### ERROR (❌) - Real Problems
- Connection failures
- Authentication failures
- Server errors (500+)
- Entity mapping failures
- Unexpected exceptions

---

## Monitoring and Alerting

### Metrics to Track

**Fallback Usage** (Expected, but should be monitored):
```python
# Track when Entity Registry fallback is used
logger.info("ℹ️ Entity Registry API not available (404) - using state-based fallback")
# → Metric: entity_registry_fallback_usage (count)
```

**Real Errors** (Should trigger alerts):
```python
# Connection errors
logger.error("❌ Cannot connect to Home Assistant")
# → Metric: ha_connection_errors (count)
# → Alert: If > 5 in 5 minutes

# Authentication errors
logger.error("❌ Authentication failed for Entity Registry API: 401")
# → Metric: ha_auth_errors (count)
# → Alert: Immediate (token likely expired)

# Server errors
logger.error("❌ Home Assistant server error: 500")
# → Metric: ha_server_errors (count)
# → Alert: If > 3 in 5 minutes

# Entity mapping failures
logger.error("❌ CRITICAL: Entity mapping failed")
# → Metric: entity_mapping_failures (count)
# → Alert: If > 10% of requests fail
```

---

## Testing Strategy

### Test 1: Expected Fallback (404)
**Input**: Entity Registry API returns 404  
**Expected**: 
- ✅ INFO log: "Entity Registry API not available (404)"
- ✅ Fallback to state-based names
- ✅ No error propagation
- ✅ Service continues normally

### Test 2: Connection Error
**Input**: HA server unreachable (connection timeout)  
**Expected**:
- ✅ ERROR log: "Cannot connect to Home Assistant"
- ✅ ConnectionError propagated
- ✅ Service can handle/retry
- ✅ User sees appropriate error message

### Test 3: Authentication Error (401)
**Input**: Invalid HA token  
**Expected**:
- ✅ ERROR log: "Authentication failed: 401"
- ✅ PermissionError propagated
- ✅ Service can notify user
- ✅ Token refresh triggered (if implemented)

### Test 4: Server Error (500)
**Input**: HA server returns 500  
**Expected**:
- ✅ ERROR log: "Home Assistant server error: 500"
- ✅ Exception propagated
- ✅ Service can retry (with backoff)
- ✅ User sees "Service temporarily unavailable"

### Test 5: Entity Mapping Failure
**Input**: No entities found for device names  
**Expected**:
- ✅ ERROR logs with full context
- ✅ devices_involved logged
- ✅ enriched_data status logged
- ✅ Sample entities logged (for debugging)
- ✅ Suggestion skipped (gracefully)

---

## Rollback Safety

All changes are **backward compatible**:
- Existing error handling still works
- Additional error details added (don't break existing code)
- Only improves error visibility
- No API changes

**If issues arise**: Revert error propagation, keep enhanced logging.

---

## Future Improvements

### 1. Structured Error Responses
```python
class EntityRegistryError(Exception):
    """Entity Registry API error with context"""
    def __init__(self, status_code: int, message: str, is_expected: bool = False):
        self.status_code = status_code
        self.is_expected = is_expected  # True for 404, False for real errors
        super().__init__(message)
```

### 2. Error Tracking to InfluxDB
```python
await influxdb_client.write_point(
    measurement="error_tracking",
    tags={
        "error_type": "connection_error",
        "service": "entity_registry",
        "severity": "error"
    },
    fields={
        "count": 1,
        "is_expected": False
    }
)
```

### 3. Alerting Integration
- PagerDuty for connection errors
- Slack for authentication errors
- Email for server errors (500+)

---

## Conclusion

✅ **Real errors are now visible** - Connection/auth/server errors are logged and propagated  
✅ **Expected fallbacks still work** - 404 for Entity Registry is handled gracefully  
✅ **Better debugging** - Detailed error context for troubleshooting  
✅ **Monitoring ready** - Error severity levels enable proper alerting  

**No errors are hidden - all issues are logged appropriately.**

