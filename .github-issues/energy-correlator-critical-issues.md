# [CRITICAL] Energy Correlator Service - N+1 Query Problem and Performance Issues

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The energy-correlator service has **CRITICAL performance issues** including massive N+1 query explosion, blocking I/O in async context, and resource leaks that will cause it to fail under production load.

---

## CRITICAL Issues

### 1. **MASSIVE N+1 QUERY PROBLEM - Performance Killer**
**Location:** `src/correlator.py:104-248`
**Severity:** CRITICAL

**Issue:** The service creates an **unbounded query explosion** that makes it impossible to keep up with processing.

```python
async def process_recent_events(self, lookback_minutes: int = 5):
    # 1. Query ALL events (NO LIMIT clause) - could return 1000+ events
    events = await self._query_recent_events(lookback_minutes)

    # 2. For EACH event, make 2 MORE queries to InfluxDB
    for event in events:
        await self._correlate_event_with_power(event)
        # ↓ This calls _get_power_at_time() TWICE
        # = 2 additional InfluxDB queries PER event
```

**Performance Calculation:**
```
100 devices × 5 state changes/min × 5 min window = 2,500 events
2,500 events × 2 queries/event = 5,000 queries + 1 initial = 5,001 queries
5,001 queries × 50ms avg = 250 seconds to process (4+ minutes)
```

**Impact:**
- With 500 events in 5 minutes (typical busy home): **1,001 queries per minute**
- Service processes every 60 seconds → **constant database overload**
- **Cannot keep up** with its own 60-second processing interval
- Violates CLAUDE.md anti-patterns: "N+1 Database Queries" and "Unbounded Queries"

**Fix:** Implement batched queries:
```python
# Query all power data in single batch
power_data = await self._query_power_batch(
    start_time=earliest_event_time - 30s,
    end_time=latest_event_time + 30s,
    entities=unique_entity_ids
)

# Process correlations in memory
for event in events:
    # Look up power data from in-memory cache
    power_before = power_data.get(event.time - 30s)
    power_after = power_data.get(event.time + 30s)
```

---

### 2. **Blocking I/O in Async Service - Event Loop Blocking**
**Location:** `src/influxdb_wrapper.py:42`
**Severity:** CRITICAL

**Issue:** InfluxDB writes use **SYNCHRONOUS** mode, blocking the entire async event loop.

```python
self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
```

**Impact:**
- Every InfluxDB write **blocks the entire async event loop**
- Under load, each write could take 10-100ms
- Blocks HTTP endpoints (/health, /statistics) during writes
- Health checks timeout during heavy correlation writes
- Service appears unresponsive
- Violates CLAUDE.md: "Blocking the Event Loop - Use async throughout"

**Fix:** Use async writes or thread pool:
```python
# Option 1: Async writes
self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)

# Option 2: Thread executor for sync writes
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, self.write_api.write, point)
```

---

### 3. **Resource Leak on Startup Failure**
**Location:** `src/main.py:154-188`
**Severity:** CRITICAL

**Issue:** InfluxDB connection not closed if startup fails.

```python
async def main():
    try:
        service = EnergyCorrelatorService()
        await service.startup()  # ← Opens InfluxDB connection

        app = await create_app(service)  # ← If this fails...
        runner = web.AppRunner(app)
        await runner.setup()  # ← Or this fails...

    finally:
        if 'service' in locals():  # ← Connection never closed!
            await service.shutdown()
```

**Impact:**
- InfluxDB connection remains open indefinitely
- Connection pool exhaustion after repeated failures
- Memory leak (InfluxDB client holds buffers)
- Service cannot restart cleanly

**Fix:** Ensure cleanup in finally block:
```python
service = None
try:
    service = EnergyCorrelatorService()
    await service.startup()
    # ... rest of startup
finally:
    if service:
        await service.shutdown()
```

---

## HIGH Severity Issues

### 4. **No Batch Writing - Performance Issue**
**Location:** `src/correlator.py:281`
**Severity:** HIGH

**Issue:** Individual writes instead of batching.

```python
async def _write_correlation(...):
    point = Point("event_energy_correlation") \
        .tag("entity_id", entity_id)

    self.client.write_point(point)  # ← Individual write, NO batching
```

**Impact:**
- 100 correlations = 100 individual InfluxDB writes
- **10-100x slower** than batch writes
- Network overhead: 100 HTTP requests vs 1 batch request
- Violates CLAUDE.md: "Batch everything (never write single points)"

**Fix:** Implement batch writing:
```python
# Accumulate points
correlation_points = []
for event in events:
    point = self._build_correlation_point(event)
    correlation_points.append(point)

# Write batch
self.client.write_batch(correlation_points)
```

---

### 5. **Silent Query Failures - Data Integrity**
**Location:** `src/influxdb_wrapper.py:92-94`
**Severity:** HIGH

**Issue:** ALL errors return empty list, hiding critical failures.

```python
def query(self, flux_query: str) -> List[Dict]:
    try:
        tables = self.query_api.query(flux_query, org=self.influxdb_org)
        return results
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return []  # ← ALL errors return empty list!
```

**Impact:**
- Cannot distinguish between:
  - "No events found" (legitimate)
  - "InfluxDB is down" (critical)
  - "Invalid credentials" (configuration error)
- No retry logic for transient failures
- Silent data loss

**Fix:** Raise exceptions for critical errors, only return empty for legitimate "no data" cases:
```python
def query(self, flux_query: str) -> List[Dict]:
    try:
        tables = self.query_api.query(flux_query, org=self.influxdb_org)
        return results
    except (ConnectionError, AuthenticationError) as e:
        logger.exception("Critical InfluxDB error")
        raise  # Don't hide critical errors
    except QueryError as e:
        if "no data" in str(e).lower():
            return []
        raise
```

---

## MEDIUM Severity Issues

### 6. **Division by Zero Risk**
**Location:** `src/correlator.py:265-268`
**Severity:** MEDIUM

**Issue:** No validation that power values are non-negative.

```python
power_delta_pct = (
    (power_delta / power_before * 100)
    if power_before > 0 else 0
)
# What if power_before is negative?
```

**Fix:** Add validation:
```python
if power_before is not None and power_before > 0:
    power_delta_pct = (power_delta / power_before * 100)
else:
    power_delta_pct = 0
```

---

### 7. **Data Integrity - No Eventually Consistent Data Handling**
**Severity:** MEDIUM

**Issue:** Late-arriving power data causes missed correlations permanently.

```python
# If power data arrives 2 minutes late:
power_before = await self._get_power_at_time(time_before)  # Returns None
power_after = await self._get_power_at_time(time_after)    # Returns None

if power_before is None or power_after is None:
    return  # ← Correlation is LOST FOREVER
```

**Impact:** No reprocessing mechanism, no backfill capability, data gaps are permanent.

**Fix:** Implement backfill mechanism or queue for retry.

---

### 8. **Port Documentation Mismatch**
**Severity:** MEDIUM

**Issue:** README says port 8015, code uses 8017.

**Fix:** Update README to reflect actual port 8017.

---

## Additional Issues

**9. No Connection Pooling:** Single InfluxDB client, no circuit breaker pattern

**10. Inefficient Time Window Queries:** `_get_power_at_time()` queries ±30 seconds but only takes first result without preferring closest match

---

## Recommended Priority Actions

1. **IMMEDIATE:** Add LIMIT clause to event queries (max 100-500 events)
2. **IMMEDIATE:** Switch to batch writing for correlations
3. **IMMEDIATE:** Use async InfluxDB operations (or run sync in thread pool)
4. **HIGH:** Fix resource leak in startup error handling
5. **HIGH:** Add proper error handling with retry logic
6. **MEDIUM:** Add data validation (non-negative power values)
7. **MEDIUM:** Implement backfill mechanism for late data

**The current implementation will fail under production load** due to the query explosion and blocking I/O patterns.

---

## References
- CLAUDE.md - Performance Patterns
- CLAUDE.md - Anti-Patterns: "N+1 Database Queries", "Unbounded Queries", "Blocking the Event Loop"
- Service location: `/services/energy-correlator/`
- Port: 8017 (NOT 8015 as documented in README)
