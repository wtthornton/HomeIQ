# [CRITICAL] WebSocket Ingestion Service - Multiple Critical Issues

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
Analysis of the websocket-ingestion service has identified **6 CRITICAL issues** that require immediate attention to prevent service crashes, data loss, and resource exhaustion.

---

## CRITICAL Issues

### 1. **Service Crashes When Entity is Deleted**
**Location:** `services/websocket-ingestion/src/event_processor.py:302-307`
**Severity:** CRITICAL

**Issue:** When a Home Assistant entity is deleted, `new_state` is None, but the code attempts to call `.get()` on it, causing an AttributeError.

```python
"state_change": {
    "from": old_state.get("state") if old_state else None,
    "to": new_state.get("state"),  # ← AttributeError if new_state is None
    "changed": old_state.get("state") != new_state.get("state") if old_state else True
}
```

**Impact:** Service crashes with AttributeError whenever any Home Assistant entity is deleted.

**Fix:** Add null check for `new_state` before accessing it.

---

### 2. **Missing InfluxDB Client Dependency**
**Location:** `services/websocket-ingestion/requirements.txt`
**Severity:** CRITICAL

**Issue:** The service uses `influxdb_client` library extensively but it's NOT listed in requirements.txt.

**Impact:** Service will fail to start with ImportError in production deployment.

**Fix:** Add `influxdb-client` to requirements.txt

---

### 3. **ClientSession Resource Leak**
**Location:** `services/websocket-ingestion/src/websocket_client.py:63`
**Severity:** CRITICAL

**Issue:** The `connect()` method creates a new `ClientSession` without checking if one already exists. During reconnection loops, multiple sessions accumulate without being closed.

**Impact:** Resource leak - unclosed sessions accumulate, eventually exhausting file descriptors and memory.

**Fix:** Check if session exists before creating, or close existing session first.

---

### 4. **Batch Processing Lock Held During Handler Execution**
**Location:** `services/websocket-ingestion/src/batch_processor.py:100-106`
**Severity:** CRITICAL

**Issue:** The batch lock is held while executing handlers, blocking all new events. This defeats async processing benefits and can cause event queue overflow.

**Impact:** Severe performance degradation, potential deadlock, event loss.

**Fix:** Release lock before calling handlers, process batch in separate task.

---

### 5. **Unbounded Memory Growth When InfluxDB is Down**
**Location:** `services/websocket-ingestion/src/influxdb_batch_writer.py`
**Severity:** CRITICAL

**Issue:** When InfluxDB is unreachable, batches accumulate in memory without bounds, leading to OOM kill.

**Scenario:** InfluxDB down for 30 minutes, events at 100/second = 180MB+ memory growth → OOM crash.

**Fix:** Implement backpressure mechanism, max queue size with overflow handling.

---

### 6. **Hardcoded Shared Module Path**
**Location:** `services/websocket-ingestion/src/main.py:17`
**Severity:** HIGH

**Issue:** Hardcoded path `/app/shared` may not exist in all environments.

**Impact:** Service fails to start if path doesn't exist.

**Fix:** Use relative path or environment variable for shared module location.

---

## Recommended Actions

1. **IMMEDIATE:** Fix entity deletion crash (Issue #1)
2. **IMMEDIATE:** Add missing dependency (Issue #2)
3. **IMMEDIATE:** Fix session leak (Issue #3)
4. **HIGH:** Fix lock contention (Issue #4)
5. **HIGH:** Implement backpressure for InfluxDB outages (Issue #5)
6. **MEDIUM:** Make shared path configurable (Issue #6)

---

## References
- CLAUDE.md Performance Patterns
- Service location: `/services/websocket-ingestion/`
- Related services: InfluxDB, data-api, admin-api
