---
status: Open
priority: Critical
service: device-intelligence-service
created: 2025-11-15
labels: [critical, bug, reliability]
---

# [CRITICAL] Device Intelligence Service - Code Errors and Resource Leaks

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The device-intelligence-service has **10 issues** including missing imports, incorrect async usage, and resource leaks that will cause immediate failures and data corruption.

---

## CRITICAL Issues

### 1. **Missing Import: `bindparam` Not Imported**
**Location:** `src/core/repository.py:217`
**Severity:** CRITICAL

**Issue:** Code uses `bindparam` without importing it from SQLAlchemy.

```python
# Line 217 uses bindparam but it's not imported
.where(Device.id == bindparam("device_id"))
```

**Impact:** Immediate `NameError` when `bulk_update_devices()` is called.

**Fix:** Add `bindparam` to SQLAlchemy imports on line 11:
```python
from sqlalchemy import select, insert, update, delete, bindparam
```

---

### 2. **Missing `await` on Async Cache Operations**
**Location:** `src/core/discovery_service.py:298`
**Severity:** CRITICAL

**Issue:** Cache deletion called without `await` keyword.

```python
# Line 298 - Missing await
cache.delete(device.id)  # Should be: await cache.delete(device.id)
```

**Impact:** Cache invalidation silently fails, causing stale data to be served.

**Fix:** Add `await` before all cache operations.

---

### 3. **Incorrect Data Type for Database Field**
**Location:** `src/core/discovery_service.py:361`
**Severity:** HIGH

**Issue:** JSON-encoding properties field when database expects Dict (JSON type).

```python
# Line 361 - Double encoding
"properties": json.dumps(capability.get("properties", {}))
# Should be:
"properties": capability.get("properties", {})
```

**Impact:** Type mismatch errors or corrupted data in database. The `DeviceCapability.properties` field is defined as `JSON` type, not `Text`.

**Fix:** Remove `json.dumps()` wrapper.

---

### 4. **Inefficient Bulk Operation Defeating Transaction Benefits**
**Location:** `src/services/device_service.py:65-78`
**Severity:** HIGH

**Issue:** `bulk_upsert_devices()` loops and commits each device individually.

```python
async def bulk_upsert_devices(self, devices_data: List[Dict[str, Any]]):
    for device_data in devices_data:
        device = await self.upsert_device(device_data)  # Commits inside loop
```

**Impact:**
- N commits instead of 1 (severe performance degradation)
- Race conditions during concurrent updates
- Partial failures leave database in inconsistent state

**Fix:** Implement true bulk operations with single commit.

---

### 5. **No Resource Cleanup on Shutdown**
**Location:** `src/main.py:61-62`
**Severity:** MEDIUM-HIGH

**Issue:** Lifespan shutdown has no cleanup logic.

```python
# Shutdown
logger.info("🛑 Device Intelligence Service shutting down...")
# Cleanup resources here  <-- Empty comment, no actual cleanup
```

**Impact:** Resource leaks on shutdown:
- Database connections not closed
- WebSocket connections left open
- MQTT connections not disconnected
- Background tasks not cancelled

**Fix:** Add proper cleanup calls for all resources.

---

### 6. **WebSocket Operations Without Timeout**
**Location:** `src/clients/ha_client.py:126, 133, 204`
**Severity:** MEDIUM-HIGH

**Issue:** WebSocket `recv()` operations have no timeout.

```python
# Lines 126, 133 - No timeout on recv
auth_response = await self.websocket.recv()
auth_result = await self.websocket.recv()

# Line 204 - Async for loop can hang forever
async for message in self.websocket:
```

**Impact:** Service hangs indefinitely during connection issues.

**Fix:** Wrap recv operations in `asyncio.wait_for()` with timeout:
```python
auth_response = await asyncio.wait_for(
    self.websocket.recv(),
    timeout=30.0
)
```

---

### 7. **Pending Messages Memory Leak**
**Location:** `src/clients/ha_client.py:86, 181-199`
**Severity:** MEDIUM

**Issue:** `pending_messages` dict can accumulate if responses never arrive.

```python
self.pending_messages: Dict[int, asyncio.Future] = {}
# Futures added but may never be removed if connection drops
```

**Impact:** Memory leak during connection instability.

**Fix:** Add cleanup logic for stale pending messages (e.g., timeout after 60 seconds).

---

### 8. **No Validation of Required Configuration Fields**
**Location:** `src/config.py:79-82`
**Severity:** MEDIUM

**Issue:** Critical fields (HA_TOKEN) are Optional with no runtime validation.

```python
HA_TOKEN: Optional[str] = Field(default=None, ...)
```

**Impact:** Service starts but fails with cryptic errors when attempting operations.

**Fix:** Add startup validation for required fields:
```python
if not config.HA_TOKEN:
    raise ValueError("HA_TOKEN is required")
```

---

### 9. **Unsafe CORS Configuration in Production**
**Location:** `src/main.py:75-81`
**Severity:** MEDIUM (Security)

**Issue:** CORS allows all origins with credentials enabled.

```python
allow_origins=["*"],  # Configure appropriately for production
allow_credentials=True,
```

**Impact:** Security vulnerability - any origin can make authenticated requests.

**Fix:** Restrict origins to known trusted domains.

---

### 10. **Missing Database Constraint Handling**
**Location:** `src/core/discovery_service.py:324`
**Severity:** MEDIUM

**Issue:** Integration field set to "unknown" as default, masking null integrations.

```python
"integration": device.integration if device.integration else "unknown"
```

**Impact:** Masks data quality issues; devices with no integration become indistinguishable.

**Fix:** Properly handle null integrations and log warnings for data quality monitoring.

---

## Recommended Action Priority

1. **IMMEDIATE:** Fix missing `bindparam` import (blocks all bulk updates)
2. **IMMEDIATE:** Add `await` to cache operations (causes data inconsistency)
3. **HIGH:** Fix JSON encoding issue (database corruption)
4. **HIGH:** Implement proper bulk operations (performance & data integrity)
5. **MEDIUM:** Add resource cleanup, timeouts, and validation

---

## References
- CLAUDE.md - Database Optimization & Async Patterns
- Service location: `/services/device-intelligence-service/`
- Port: 8028
- Database: `device_intelligence.db` (7 tables)
