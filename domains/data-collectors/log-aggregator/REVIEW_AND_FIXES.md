# Log Aggregator -- Deep Code Review & Fix Plan

**Service:** `log-aggregator` (Port 8015, Tier 4 -- Enhanced Data Sources)
**Review Date:** 2026-02-06
**Reviewer:** Claude Opus 4.6 (automated deep review)
**Total Findings:** 4 CRITICAL | 7 HIGH | 10 MEDIUM | 10 LOW = 31

---

## Executive Summary

The log-aggregator collects Docker container logs, stores them in memory, and serves them via REST API. It has a clear, focused purpose and a multi-stage Docker build. However, critical issues include: unvalidated `limit` parameter causing crashes, Docker socket access granting full host control, no authentication on the log collection trigger, and arbitrary JSON injection from container logs. The advertised file persistence feature is not implemented despite being documented in the README.

---

## CRITICAL Issues (Must Fix)

### CRITICAL-01: Unvalidated `limit` Parameter Causes Crash

**File:** `src/main.py` lines 166, 183

`limit = int(request.query.get('limit', 100))` -- `?limit=abc` raises unhandled ValueError (500). No upper bound, so `?limit=999999999` forces expensive copy/sort/serialize of entire buffer.

**Fix:**
```python
try:
    limit = int(request.query.get('limit', 100))
    if limit < 1 or limit > 10000:
        return web.json_response({"error": "limit must be between 1 and 10000"}, status=400)
except (ValueError, TypeError):
    return web.json_response({"error": "limit must be a valid integer"}, status=400)
```

---

### CRITICAL-02: Docker Socket Access Grants Full Host Control

**Files:** `src/main.py` line 34, `docker-compose.yml` lines 842-846

`docker.from_env()` + socket mount + group `"0"` (root). `:ro` flag does NOT restrict Docker API operations. If compromised, attacker can start/stop/delete any container, execute commands, mount host filesystems.

**Fix:** Use Docker socket proxy (Tecnativa/docker-socket-proxy) exposing only CONTAINERS and LOG operations.

---

### CRITICAL-03: No Authentication on Log Collection Trigger

**File:** `src/main.py` lines 199-207

`POST /api/v1/logs/collect` triggers full log collection across all Docker containers. Zero auth, zero rate limiting. Service constrained to 128MB / 0.5 CPUs.

**Fix:** Add API key check + rate limiting (10s cooldown).

---

### CRITICAL-04: Arbitrary JSON Injection via Container Logs

**File:** `src/main.py` lines 47-52

JSON log lines accepted verbatim with no schema validation or size limits. Malicious container can spoof `service` field, inject arbitrary fields, or send 100MB JSON line to crash the service.

**Fix:** Enforce max line length (64KB), normalize to expected schema, always use `container_name` as `service` (not self-reported).

---

## HIGH Issues (Should Fix)

### HIGH-01: Synchronous Docker API Calls Block Async Event Loop

**File:** `src/main.py` lines 72-76, 96

`docker.containers.list()` and `container.logs()` are synchronous HTTP calls via `requests`. Called directly in async methods without executor. With ~25 containers, blocks event loop for seconds. Health checks become unresponsive during collection.

**Fix:** `containers = await loop.run_in_executor(None, lambda: self.docker_client.containers.list(all=False))`

---

### HIGH-02: Duplicate Log Entries Accumulate Without Deduplication

**File:** `src/main.py` lines 71-108

Every 30s, fetches last 100 lines per container. If container produces < 100 new lines per 30s (common case), same lines re-fetched and re-appended. 10,000-entry buffer fills with duplicates in ~2 minutes.

**Fix:** Track `since` timestamp per container:
```python
self._last_seen: dict[str, datetime] = {}
# Use since= parameter instead of tail=
```

---

### HIGH-03: Full 10,000-Entry List Copied and Sorted on Every Query

**File:** `src/main.py` lines 117-135

Every `/api/v1/logs` call: copy 10,000 entries, filter, O(n log n) sort, then slice. With 128MB limit and concurrent requests, this causes memory pressure.

**Fix:** Use `collections.deque(maxlen=10000)`, maintain insertion order, filter-then-sort.

---

### HIGH-04: Documented Environment Variables Not Used in Code

| Variable | Documented | Actual Code |
|---|---|---|
| `LOG_DIRECTORY` | `/app/logs` | Hardcoded |
| `MAX_LOGS_MEMORY` | `10000` | Hardcoded |
| `COLLECTION_INTERVAL` | `30` | Hardcoded |

Operators following README see no effect.

**Fix:** Read from `os.getenv()`.

---

### HIGH-05: File Persistence Advertised But Never Implemented

README claims file storage, `aiofiles` dependency installed, directory created, docker-compose mounts volume. But no file write anywhere in code. All logs lost on restart.

**Fix:** Either implement file persistence using `aiofiles`, or correct README and remove unused dependency.

---

### HIGH-06: Timezone-Naive vs Timezone-Aware Comparison in Statistics

**File:** `src/main.py` lines 209-221

`datetime.utcnow()` (naive) vs parsed log timestamps (aware). On non-UTC systems, cutoff offset by timezone difference. Also `utcnow()` deprecated in Python 3.12.

**Fix:** Use `datetime.now(timezone.utc)` consistently.

---

### HIGH-07: Background Task Reference Dropped -- Silent Death with No Recovery

**File:** `src/main.py` line 290

`asyncio.create_task(background_log_collection())` -- reference discarded. If task dies, service reports healthy but stops collecting. No monitoring, no restart.

**Fix:** Store reference, add `done_callback`, check in health endpoint.

---

## MEDIUM Issues (Nice to Fix)

| # | Issue | Fix |
|---|---|---|
| M-01 | CORS hardcoded to localhost, allows unused HTTP methods | Configurable via CORS_ORIGINS env, restrict to GET/POST/OPTIONS |
| M-02 | No request body size limits | `web.Application(client_max_size=64*1024)` |
| M-03 | Non-JSON logs missing `service` field | Add `'service': container_name` to non-JSON branch |
| M-04 | Search scans entire buffer regardless of limit | Pre-compute `query.lower()`, consider early termination |
| M-05 | Global mutable state at module import time | Use aiohttp app state pattern |
| M-06 | Tests mock at `sys.modules` level | Use `unittest.mock.patch` with proper scoping |
| M-07 | 14+ key test scenarios missing | Add tests for limit validation, concurrent access, etc. |
| M-08 | `datetime.utcnow()` deprecated in Python 3.12 | Use `datetime.now(timezone.utc)` |
| M-09 | `_count_by_field` can produce non-string dict keys | `value = str(log.get(field, 'unknown'))` |
| M-10 | `aiohttp-cors` unmaintained since 2020 | Replace with built-in middleware |

---

## LOW Issues (Optional)

| # | Issue | Fix |
|---|---|---|
| L-01 | `aiofiles` dependency unused | Remove (or implement persistence) |
| L-02 | Emoji in production log messages | Use plain text markers |
| L-03 | Health always reports "healthy" even with Docker down | Return 503 when Docker client is None |
| L-04 | Fragile `sys.path` manipulation | Use try/except guard |
| L-05 | `.dockerignore` in service dir has no effect (context is repo root) | Document or move |
| L-06 | Container errors silenced at DEBUG level | Use WARNING |
| L-07 | No graceful shutdown of background task | Cancel task in finally block |
| L-08 | Dockerfile installs gcc but no C extensions compiled | Remove gcc |
| L-09 | Docker cache mount and --no-cache-dir contradict | Remove --no-cache-dir |
| L-10 | Listens on 0.0.0.0 with port exposed to host | Document security implications |

---

## Priority Fix Order

| # | Finding | Effort | Impact |
|---|---|---|---|
| 1 | CRITICAL-01: Validate limit parameter | 10 min | Prevents crashes |
| 2 | CRITICAL-04: Schema validation on JSON logs | 20 min | Prevents memory exhaustion |
| 3 | HIGH-01: Run Docker calls in executor | 15 min | Unblocks event loop |
| 4 | HIGH-02: Add deduplication | 20 min | Prevents buffer pollution |
| 5 | HIGH-04: Wire up environment variables | 10 min | Enables operational tuning |
| 6 | HIGH-06: Fix timezone handling | 10 min | Correct statistics |
| 7 | HIGH-07: Store/monitor background task | 10 min | Prevents silent failures |
| 8 | CRITICAL-03: Add rate limiting to collect endpoint | 15 min | Prevents DoS |
| 9 | CRITICAL-02: Docker socket proxy | 30 min | Reduces blast radius |
| 10 | HIGH-05: Implement persistence or fix README | 30 min | Removes confusion |

---

## Architecture Assessment

### Strengths
1. Clear, focused purpose -- collect Docker logs, store in memory, serve via API
2. Multi-stage Docker build with non-root user
3. Health check follows HomeIQ convention
4. Error backoff in background task (30s normal, 60s on error)
5. Comprehensive README (despite accuracy issues)
6. Resource limits in docker-compose (128MB, 0.5 CPUs)
7. Docker log rotation configured

### Weaknesses
1. No InfluxDB integration (unlike other HomeIQ services)
2. No data-api integration
3. In-memory only storage (complete data loss on restart)
4. Sync-in-async anti-pattern (Docker SDK)
5. No input validation on any endpoint
6. Self-monitoring feedback loop (collects own logs)
7. No log deduplication
8. Misleading documentation (file persistence not implemented)

---

**Maintained by:** HomeIQ DevOps Team
**Last Updated:** February 6, 2026
