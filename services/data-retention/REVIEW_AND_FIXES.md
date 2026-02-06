# Data Retention Service - Comprehensive Code Review

**Service**: data-retention (Tier 2, port 8080)
**Review Date**: 2026-02-06
**Reviewer**: Claude Opus 4.6 (Automated Deep Review)
**Files Reviewed**: 26 source files, 6 test files, 2 Dockerfiles, 2 requirements files

---

## Executive Summary

**Overall Health Score: 5.5 / 10**

The data-retention service has a solid foundational architecture with good separation of concerns across multiple modules (cleanup, compression, backup, tiered retention, scheduling, etc.). However, it suffers from several **critical security vulnerabilities** (SQL injection, path traversal, zip slip), **incomplete implementations** (many mock-only code paths), **dual framework confusion** (both aiohttp and FastAPI coexist), **unbounded memory growth** patterns, and **significant test coverage gaps**. The service is functional for basic operations but needs substantial hardening before production deployment.

### Score Breakdown
| Area | Score | Notes |
|------|-------|-------|
| Code Quality | 6/10 | Good structure, some dead code and duplication |
| Security | 3/10 | SQL injection, path traversal, zip slip, no auth, CORS wildcard |
| Error Handling | 6/10 | Consistent try/except but error messages leak internals |
| Performance | 5/10 | Unbounded history growth, N+1 queries, blocking compression |
| Test Coverage | 4/10 | ~40% of modules tested, zero tests for 10+ modules |
| Docker | 7/10 | Good multi-stage build, minor improvements possible |
| API Design | 6/10 | Two competing frameworks, reasonable REST patterns |
| Observability | 5/10 | Logging present but no metrics/tracing integration |

---

## CRITICAL Issues (Must Fix)

### C1. SQL Injection in Materialized Views `query_view()`

**File**: `c:\cursor\HomeIQ\services\data-retention\src\materialized_views.py`, lines 226-250
**Severity**: CRITICAL
**OWASP**: A03:2021 - Injection

The `query_view()` method directly interpolates user-supplied `view_name` and `filters` into SQL queries without any sanitization or parameterization.

```python
# VULNERABLE CODE (lines 233-246)
async def query_view(self, view_name: str, filters: dict[str, Any] = None) -> list[dict]:
    query = f"SELECT * FROM {view_name}"  # SQL INJECTION via view_name!

    if filters:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f"{key} = '{value}'")  # SQL INJECTION via key AND value!
            else:
                conditions.append(f"{key} = {value}")  # SQL INJECTION via key AND value!

        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

    query += " ORDER BY time DESC LIMIT 1000"
    result = self.client.query(query, language='sql', mode='pandas')
```

**Impact**: An attacker could read, modify, or delete any data in InfluxDB. Could also potentially execute administrative commands.

**Recommended Fix**:
```python
import re

VALID_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

async def query_view(self, view_name: str, filters: dict[str, Any] = None) -> list[dict]:
    if not self.enabled:
        logger.debug("Materialized views disabled - cannot query view")
        return []

    # Validate view_name is a safe identifier
    if not VALID_IDENTIFIER.match(view_name):
        raise ValueError(f"Invalid view name: {view_name}")

    # Whitelist allowed view names
    allowed_views = {
        "mv_daily_energy_by_device",
        "mv_hourly_room_activity",
        "mv_daily_carbon_summary",
    }
    if view_name not in allowed_views:
        raise ValueError(f"Unknown view: {view_name}")

    query = f"SELECT * FROM {view_name}"

    if filters:
        conditions = []
        for key, value in filters.items():
            # Validate key is a safe identifier
            if not VALID_IDENTIFIER.match(key):
                raise ValueError(f"Invalid filter key: {key}")
            # Use parameterized values (escape single quotes in strings)
            if isinstance(value, str):
                safe_value = value.replace("'", "''")
                conditions.append(f"{key} = '{safe_value}'")
            elif isinstance(value, (int, float)):
                conditions.append(f"{key} = {value}")
            else:
                raise ValueError(f"Unsupported filter value type: {type(value)}")

        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"

    query += " ORDER BY time DESC LIMIT 1000"
    result = self.client.query(query, language='sql', mode='pandas')
    return result.to_dict('records') if not result.empty else []
```

---

### C2. SQL Injection in Tiered Retention and S3 Archival Queries

**File**: `c:\cursor\HomeIQ\services\data-retention\src\tiered_retention.py`, lines 87-100, 152-165
**File**: `c:\cursor\HomeIQ\services\data-retention\src\s3_archival.py`, lines 101-106
**Severity**: CRITICAL
**OWASP**: A03:2021 - Injection

Timestamp values are formatted using Python f-strings directly into SQL:

```python
# tiered_retention.py line 98
query = f'''
SELECT ...
FROM home_assistant_events
WHERE time < TIMESTAMP '{cutoff_date.isoformat()}'  # Unparameterized
GROUP BY ...
'''
```

While these are currently generated internally from `datetime.now()` and not from user input, this pattern establishes a dangerous precedent. If any code path allows user-influenced date values (e.g., custom retention periods, manual trigger endpoints), this becomes exploitable.

**Recommended Fix**: Use parameterized queries or at minimum validate that the interpolated value conforms to ISO 8601 format before inclusion in the query string.

---

### C3. Zip Slip Vulnerability in Backup Restore (Path Traversal)

**File**: `c:\cursor\HomeIQ\services\data-retention\src\backup_restore.py`, lines 330-335
**Severity**: CRITICAL
**OWASP**: A01:2021 - Broken Access Control

The `restore_backup()` method extracts tar archives without validating that extracted paths don't escape the target directory:

```python
# VULNERABLE CODE (line 334-335)
with tarfile.open(backup_file, "r:gz") as tar:
    tar.extractall(temp_path)  # ZIP SLIP - no path validation!
```

A maliciously crafted tar archive could contain entries like `../../etc/passwd` that write files anywhere on the filesystem.

**Recommended Fix**:
```python
import os

def _safe_extract(tar, path):
    """Safely extract tar archive, preventing path traversal."""
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        abs_path = os.path.realpath(member_path)
        abs_target = os.path.realpath(str(path))
        if not abs_path.startswith(abs_target + os.sep) and abs_path != abs_target:
            raise ValueError(f"Path traversal detected in archive: {member.name}")
    tar.extractall(path, filter='data')  # Python 3.12+ filter parameter

# Usage:
with tarfile.open(backup_file, "r:gz") as tar:
    _safe_extract(tar, temp_path)
```

Note: Python 3.12+ supports `tar.extractall(path, filter='data')` which prevents path traversal natively.

---

### C4. Arbitrary File Read/Write via Backup Config Restore

**File**: `c:\cursor\HomeIQ\services\data-retention\src\backup_restore.py`, lines 411-432
**Severity**: CRITICAL
**OWASP**: A01:2021 - Broken Access Control

The `_restore_config()` method writes files to `/app/` with names derived from the backup archive without validation:

```python
# VULNERABLE CODE (lines 425-428)
for config_file in config_dir.iterdir():
    if config_file.is_file():
        dest_path = f"/app/{config_file.name}"  # Filename from archive!
        shutil.copy2(config_file, dest_path)     # Overwrites ANY file in /app/
```

An attacker could craft a backup with config files named `../etc/cron.d/backdoor` or `main.py` to overwrite critical service code.

**Recommended Fix**: Whitelist allowed config filenames and validate paths:
```python
ALLOWED_CONFIG_FILES = {"config.yaml", ".env", "influxdb.conf"}

for config_file in config_dir.iterdir():
    if config_file.is_file() and config_file.name in ALLOWED_CONFIG_FILES:
        dest_path = Path("/app") / config_file.name
        # Verify path doesn't escape target directory
        if not dest_path.resolve().is_relative_to(Path("/app").resolve()):
            logger.warning(f"Skipping suspicious config file: {config_file.name}")
            continue
        shutil.copy2(config_file, dest_path)
```

---

### C5. No Authentication or Authorization on Any Endpoint

**File**: `c:\cursor\HomeIQ\services\data-retention\src\api\app.py` and all routers
**Severity**: CRITICAL
**OWASP**: A07:2021 - Identification and Authentication Failures

Every API endpoint is completely unauthenticated. The following destructive operations are exposed without any access control:

- `POST /cleanup` - Deletes data from InfluxDB
- `POST /backup/restore` - Overwrites data and config files
- `DELETE /policies/{name}` - Deletes retention policies
- `DELETE /backup/cleanup` - Deletes backup files
- `POST /retention/downsample-hourly` - Modifies data
- `POST /retention/archive-s3` - Moves data to S3

**Recommended Fix**: Add at minimum an API key middleware:
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    expected_key = os.getenv("DATA_RETENTION_API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Apply to routers that perform mutations:
router = APIRouter(prefix="/backup", tags=["backup"], dependencies=[Depends(verify_api_key)])
```

---

### C6. CORS Wildcard Allows Any Origin

**File**: `c:\cursor\HomeIQ\services\data-retention\src\api\app.py`, lines 50-57
**Severity**: CRITICAL
**OWASP**: A05:2021 - Security Misconfiguration

```python
# VULNERABLE CODE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Any website can make requests!
    allow_credentials=True,        # WITH credentials!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact**: `allow_origins=["*"]` combined with `allow_credentials=True` is invalid per the CORS specification, but some browsers may behave unexpectedly. Any malicious website could make authenticated cross-origin requests to this service.

**Recommended Fix**:
```python
ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
```

---

## HIGH Priority Issues

### H1. Unbounded In-Memory History Growth (Memory Leak)

**Files**:
- `c:\cursor\HomeIQ\services\data-retention\src\data_cleanup.py`, line 53: `self.cleanup_history: list[CleanupResult] = []`
- `c:\cursor\HomeIQ\services\data-retention\src\data_compression.py`, line 65: `self.compression_history: list[CompressionResult] = []`
- `c:\cursor\HomeIQ\services\data-retention\src\backup_restore.py`, line 58: `self.backup_history: list[BackupInfo] = []`

**Severity**: HIGH

These lists grow indefinitely without any pruning. Over weeks/months of operation, these will consume increasing memory, eventually leading to OOM crashes.

Only `StorageMonitor` (line 152) has a cap at 1000 entries. The others do not.

**Recommended Fix**: Add bounded history to all services:
```python
MAX_HISTORY_SIZE = 1000

# After appending to history:
if len(self.cleanup_history) > MAX_HISTORY_SIZE:
    self.cleanup_history = self.cleanup_history[-MAX_HISTORY_SIZE:]
```

Or better, use `collections.deque(maxlen=1000)`.

---

### H2. Dual Framework Confusion (aiohttp + FastAPI)

**Files**:
- `c:\cursor\HomeIQ\services\data-retention\src\health_check.py` - Uses `aiohttp.web`
- `c:\cursor\HomeIQ\services\data-retention\src\retention_endpoints.py` - Uses `aiohttp.web`
- `c:\cursor\HomeIQ\services\data-retention\src\api\app.py` - Uses FastAPI
- `c:\cursor\HomeIQ\services\data-retention\src\api\routers\*` - Uses FastAPI

**Severity**: HIGH

The service has two parallel API layers:
1. **aiohttp** endpoints in `health_check.py` and `retention_endpoints.py`
2. **FastAPI** routers in `src/api/routers/`

The FastAPI app (`src/api/app.py`) is the actual running application, but the aiohttp endpoints in `health_check.py` and `retention_endpoints.py` are dead code that will never be served. The `main.py` even imports `RetentionEndpoints` but the `setup_epic2_endpoints()` method is documented as deprecated.

**Recommended Fix**: Remove the dead aiohttp endpoints entirely:
- Delete `src/health_check.py` (replaced by `src/api/routers/health.py`)
- Delete `src/retention_endpoints.py` (replaced by `src/api/routers/retention.py`)
- Remove `aiohttp` from production dependencies if no longer needed elsewhere
- Remove `setup_epic2_endpoints()` from `main.py`

---

### H3. Blocking Compression Operations in Async Context

**File**: `c:\cursor\HomeIQ\services\data-retention\src\data_compression.py`, lines 117-123
**Severity**: HIGH

CPU-intensive compression operations (`gzip.compress`, `lzma.compress`, `zlib.compress`) are called synchronously within async methods, blocking the event loop:

```python
# BLOCKING CODE in async method
async def compress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> CompressionResult:
    # ...
    if algorithm == CompressionAlgorithm.GZIP:
        compressed_data = gzip.compress(data, compresslevel=9)  # BLOCKS event loop!
    elif algorithm == CompressionAlgorithm.LZMA:
        compressed_data = lzma.compress(data, preset=9)         # BLOCKS event loop!
```

With `compresslevel=9` and `preset=9` (maximum compression), large data sets could block the event loop for seconds, making health checks fail and other API requests timeout.

**Recommended Fix**:
```python
import asyncio
from functools import partial

async def compress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> CompressionResult:
    loop = asyncio.get_event_loop()
    if algorithm == CompressionAlgorithm.GZIP:
        compressed_data = await loop.run_in_executor(
            None, partial(gzip.compress, data, compresslevel=6)  # Use level 6 for better balance
        )
    # ... same pattern for other algorithms
```

---

### H4. `find_best_compression()` Compresses Data 3x Unnecessarily

**File**: `c:\cursor\HomeIQ\services\data-retention\src\data_compression.py`, lines 165-193
**Severity**: HIGH

The `find_best_compression()` method calls `compress_data()` for all three algorithms, each of which appends to `compression_history`. This means:
1. Every call wastes CPU by compressing with all 3 algorithms when only 1 result is used
2. 3 entries are added to compression history for every logical compression operation
3. The `compression_history` inflates statistics and memory usage

**Recommended Fix**: Use a separate internal method that doesn't track history, or add a `track_history=False` parameter.

---

### H5. Global Module-Level Service Instance Creates Import Side Effects

**File**: `c:\cursor\HomeIQ\services\data-retention\src\main.py`, line 292
**Severity**: HIGH

```python
# Global service instance
data_retention_service = DataRetentionService()
```

This creates a `DataRetentionService` instance at module import time, which:
1. Creates the `RetentionPolicyManager` and reads environment variables
2. Gets imported by `health_check.py` (line 8), creating a circular dependency risk
3. Is separate from the instance created in `app.py` lifespan (line 26), meaning TWO separate instances exist

The `app.py` lifespan creates its own `DataRetentionService()` and stores it in `app.state.service`, while `health_check.py` imports `data_retention_service` from `main.py`. The FastAPI routers correctly use `request.app.state.service`, but the aiohttp health_check uses the wrong instance.

**Recommended Fix**: Remove the global instance and use dependency injection through FastAPI's app state exclusively.

---

### H6. Statistics Aggregator Has N+1 Query Problem

**File**: `c:\cursor\HomeIQ\services\data-retention\src\statistics_aggregator.py`, lines 131-208
**Severity**: HIGH

For each entity, the aggregator makes 1-3 separate InfluxDB queries (mean, min, max). With hundreds of entities, this creates a massive N+1 query problem:

```python
for entity in eligible_entities:  # Could be 100+ entities
    # Query 1: mean
    mean_query = base_query + '|> aggregateWindow(every: 5m, fn: mean, ...)'
    result = self.query_api.query(mean_query)

    if has_mean and mean_values:
        # Query 2: min
        min_result = self.query_api.query(min_query)
        # Query 3: max
        max_result = self.query_api.query(max_query)
```

With 200 entities, this could be 200-600 queries every 5 minutes!

**Recommended Fix**: Batch entities into a single Flux query using `filter(fn: (r) => r.entity_id == "a" or r.entity_id == "b" ...)` or use InfluxDB tasks for continuous aggregation.

---

### H7. SQLite Connection Not Using Context Manager / Connection Pool

**File**: `c:\cursor\HomeIQ\services\data-retention\src\statistics_aggregator.py`, lines 71-95
**Severity**: HIGH

```python
def _get_eligible_entities(self) -> list[dict[str, Any]]:
    try:
        import sqlite3
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT statistic_id, state_class, has_mean, has_sum, unit_of_measurement
            FROM statistics_meta
        """)
        entities = []
        for row in cursor.fetchall():
            entities.append({...})
        conn.close()  # No finally block - connection leaked on exception!
        return entities
    except Exception as e:
        logger.error(f"Error fetching eligible entities from SQLite: {e}")
        return []
```

If an exception occurs between `connect()` and `close()`, the connection is leaked. Also, `fetchall()` loads the entire result set into memory.

**Recommended Fix**:
```python
def _get_eligible_entities(self) -> list[dict[str, Any]]:
    try:
        import sqlite3
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT statistic_id, state_class, has_mean, has_sum, unit_of_measurement
                FROM statistics_meta
            """)
            return [
                {
                    "statistic_id": row["statistic_id"],
                    "state_class": row["state_class"],
                    "has_mean": bool(row["has_mean"]),
                    "has_sum": bool(row["has_sum"]),
                    "unit_of_measurement": row["unit_of_measurement"]
                }
                for row in cursor
            ]
    except Exception as e:
        logger.error(f"Error fetching eligible entities from SQLite: {e}")
        return []
```

---

### H8. Error Messages Leak Internal Details to API Consumers

**Files**: All router files in `src/api/routers/`
**Severity**: HIGH
**OWASP**: A04:2021 - Insecure Design

All error handlers pass raw exception messages to the HTTP response:

```python
# Example from routers/backup.py line 38
except Exception as e:
    raise HTTPException(status_code=500, detail={"error": str(e)})
```

This leaks internal details like file paths, database connection strings, stack traces from libraries, etc.

**Recommended Fix**: Log the full error internally but return a generic message:
```python
except Exception as e:
    logger.error(f"Backup creation failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail={"error": "Internal server error"})
```

---

## MEDIUM Priority Issues

### M1. Deprecated `datetime.utcnow()` Usage Throughout

**Files**: Almost every file in `src/`
**Severity**: MEDIUM

`datetime.utcnow()` is deprecated in Python 3.12+. The code uses it extensively:

```python
# Found in: main.py, data_cleanup.py, data_compression.py, health_check.py,
# retention_policy.py, storage_monitor.py, backup_restore.py
datetime.utcnow()  # DEPRECATED
```

Some files (like `statistics_aggregator.py`) correctly use `datetime.now(timezone.utc)`, showing inconsistency.

**Recommended Fix**: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`:
```python
from datetime import datetime, timezone

# Before:
datetime.utcnow()

# After:
datetime.now(timezone.utc)
```

---

### M2. Duplicate `if not self.enabled` Check in `refresh_all_views()`

**File**: `c:\cursor\HomeIQ\services\data-retention\src\materialized_views.py`, lines 191-197

```python
async def refresh_all_views(self):
    if not self.enabled:  # Check 1
        logger.debug("Materialized views disabled - skipping refresh")
        return {'status': 'disabled', 'reason': 'InfluxDB 3.0+ required'}

    if not self.enabled:  # Check 2 - EXACT DUPLICATE
        logger.debug("Materialized views disabled - skipping refresh")
        return {'status': 'disabled', 'reason': 'InfluxDB 3.0+ required'}
```

**Recommended Fix**: Remove the duplicate check (lines 195-197).

---

### M3. Duplicate `if __name__ == "__main__"` Block

**File**: `c:\cursor\HomeIQ\services\data-retention\src\pattern_aggregate_retention.py`, lines 186-198

```python
if __name__ == "__main__":      # Line 186
    import asyncio

    async def main():
        results = await run_pattern_aggregate_retention()
        print("Pattern Aggregate Retention Results:")
        # ...

# Run if executed directly
if __name__ == "__main__":      # Line 197 - DUPLICATE
    asyncio.run(main())
```

The `main()` function is defined inside the first `if __name__` block but called in the second one. This works but is confusing and fragile.

**Recommended Fix**: Merge into a single block:
```python
if __name__ == "__main__":
    import asyncio

    async def main():
        results = await run_pattern_aggregate_retention()
        print(f"Duration: {results['duration_seconds']:.2f}s")
        for bucket, result in results['results'].items():
            status = 'OK' if result['success'] else 'FAIL'
            print(f"  {bucket}: {status}")

    asyncio.run(main())
```

---

### M4. Division by Zero Potential in Compression Ratio

**File**: `c:\cursor\HomeIQ\services\data-retention\src\data_compression.py`, line 128

```python
compression_ratio = compressed_size / original_size  # Fails if original_size == 0!
```

If `compress_data()` is called with empty bytes (`b""`), `original_size` will be 0, causing `ZeroDivisionError`.

**Recommended Fix**:
```python
compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
```

---

### M5. S3 Client Initialized in `__init__` Even When Not Configured

**File**: `c:\cursor\HomeIQ\services\data-retention\src\s3_archival.py`, lines 50-56

```python
if self.s3_bucket:
    self.s3_client = boto3.client(
        's3',
        region_name=self.aws_region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
```

This creates an S3 client in `__init__`, which could fail and prevent the entire service from starting if AWS credentials are misconfigured. Also, the credentials are fetched from env vars at construction time rather than being refreshed.

**Recommended Fix**: Defer S3 client creation to first use with a factory method.

---

### M6. `asyncio-mqtt` in Requirements but Never Used

**File**: `c:\cursor\HomeIQ\services\data-retention\requirements.txt`, line 7

```
asyncio-mqtt>=0.16.1,<1.0.0
```

No source file imports `asyncio_mqtt` or `aiomqtt`. This is a dead dependency that increases the attack surface and image size.

**Recommended Fix**: Remove `asyncio-mqtt` from `requirements.txt`.

---

### M7. `pytest` Dependencies in Production Requirements

**File**: `c:\cursor\HomeIQ\services\data-retention\requirements.txt`, lines 13-15

```
pytest>=8.3.3
pytest-asyncio>=0.23.0
pytest-cov>=5.0.0
```

Test dependencies should not be in the main requirements file. The production Dockerfile (`Dockerfile`) correctly uses `requirements-prod.txt` which does not include them, but the dev Dockerfile uses `requirements.txt`.

**Recommended Fix**: Move test dependencies to a separate `requirements-dev.txt` or `requirements-test.txt`.

---

### M8. Pydantic Model Uses Deprecated `.dict()` Method

**File**: `c:\cursor\HomeIQ\services\data-retention\src\api\routers\policies.py`, lines 36, 53

```python
service.add_retention_policy(policy.dict())     # .dict() deprecated in Pydantic v2
service.update_retention_policy(policy.dict())   # Use .model_dump() instead
```

**Recommended Fix**:
```python
service.add_retention_policy(policy.model_dump())
service.update_retention_policy(policy.model_dump())
```

---

### M9. Temp Files Not Cleaned Up on Error in S3 Archival

**File**: `c:\cursor\HomeIQ\services\data-retention\src\s3_archival.py`, lines 117-147

```python
with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.parquet') as f:
    parquet_file = f.name
    pq.write_table(table, f, compression='gzip')

# ... if any exception occurs between here and line 147, temp file is leaked
os.remove(parquet_file)  # Only reached on success path
```

**Recommended Fix**: Use a try/finally block:
```python
parquet_file = None
try:
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.parquet') as f:
        parquet_file = f.name
        pq.write_table(table, f, compression='gzip')
    # ... upload to S3
finally:
    if parquet_file and os.path.exists(parquet_file):
        os.remove(parquet_file)
```

---

### M10. Policy Validation Not Called During Add/Update

**File**: `c:\cursor\HomeIQ\services\data-retention\src\retention_policy.py`

The `RetentionPolicyManager` has a `validate_policy()` method (line 177) but it is never called in `add_policy()` or `update_policy()`. Invalid policies (negative retention period, empty name, etc.) can be added without checks.

**Recommended Fix**:
```python
def add_policy(self, policy: RetentionPolicy) -> None:
    errors = self.validate_policy(policy)
    if errors:
        raise ValueError(f"Invalid policy: {'; '.join(errors)}")
    if policy.name in self.policies:
        raise ValueError(f"Policy '{policy.name}' already exists")
    self.policies[policy.name] = policy
```

---

### M11. `add_retention_policy` Expects Enum but API Sends String

**File**: `c:\cursor\HomeIQ\services\data-retention\src\main.py`, lines 156-166

The `add_retention_policy()` method wraps data from API input:
```python
def add_retention_policy(self, policy_data: dict) -> None:
    policy = RetentionPolicy(
        retention_unit=RetentionPeriod(policy_data["retention_unit"]),  # Expects enum value string
    )
```

But the Pydantic model for `PolicyCreateRequest` has `description: Optional[str] = None`, and `add_retention_policy` accesses `policy_data["description"]` without checking for `None`, which would set the policy description to `None`. The `validate_policy()` method would flag this as "Policy description is required", but as noted in M10, validation is never called.

---

## LOW Priority / Nice-to-Have

### L1. Inconsistent Port Configuration

**File**: `c:\cursor\HomeIQ\services\data-retention\src\main.py`, line 303

```python
port = int(os.getenv('PORT', '8080'))
```

Good -- matches the Dockerfile EXPOSE and the documented port.

---

### L2. No Request Body Size Limits

**Files**: FastAPI routers
**Severity**: LOW

The FastAPI application does not configure request body size limits. A client could send very large JSON payloads to `POST /backup`, `POST /policies`, etc., potentially causing memory exhaustion.

**Recommended Fix**: Configure uvicorn with `--limit-max-request-size` or add a custom middleware.

---

### L3. Scheduler Polling Loop Resolution

**File**: `c:\cursor\HomeIQ\services\data-retention\src\scheduler.py`, line 97

The scheduler sleeps for 60 seconds between checks. This means:
1. Tasks scheduled at a specific minute might be missed if the check happens at second 59 and the next check at second 59 of the next minute
2. Periodic tasks with intervals less than 1 minute cannot be scheduled

This is acceptable for current use but not ideal for precision scheduling.

---

### L4. Missing `__all__` Exports in `__init__.py`

**File**: `c:\cursor\HomeIQ\services\data-retention\src\__init__.py`

The init file only contains the version string. It does not export any public API, making it unclear what the public interface of the package is.

---

### L5. `aiohttp` Still in Requirements

**File**: `c:\cursor\HomeIQ\services\data-retention\requirements.txt`, line 6

`aiohttp` is imported only in the dead code (`health_check.py`, `retention_endpoints.py`). If those files are removed per H2, aiohttp can also be removed from dependencies.

---

### L6. `schedule` Package in Production Requirements Unused

**File**: `c:\cursor\HomeIQ\services\data-retention\requirements-prod.txt`, line 8

```
schedule==1.2.1
```

The `schedule` package is not imported anywhere in the source code. The service uses a custom `RetentionScheduler` (scheduler.py) instead.

---

### L7. Rollback Script Files Left in Service Directory

**Files**:
- `c:\cursor\HomeIQ\services\data-retention\rollback_pytest_asyncio_20260205_143732.sh`
- `c:\cursor\HomeIQ\services\data-retention\rollback_pytest_asyncio_20260205_143930.sh`
- `c:\cursor\HomeIQ\services\data-retention\rollback_mqtt_20260205_143931.sh`
- `c:\cursor\HomeIQ\services\data-retention\Dockerfile.backup_20260102_115804`

These should be cleaned up. Rollback scripts and backup Dockerfiles shouldn't persist in the repo.

---

## Security Findings Summary

| ID | Finding | Severity | OWASP | File |
|----|---------|----------|-------|------|
| C1 | SQL Injection in `query_view()` | CRITICAL | A03 | materialized_views.py:233-246 |
| C2 | SQL Injection in tiered retention queries | CRITICAL | A03 | tiered_retention.py:87-100 |
| C3 | Zip Slip in `tar.extractall()` | CRITICAL | A01 | backup_restore.py:334 |
| C4 | Arbitrary file write via config restore | CRITICAL | A01 | backup_restore.py:425-428 |
| C5 | No authentication on any endpoint | CRITICAL | A07 | api/app.py (all routers) |
| C6 | CORS wildcard with credentials | CRITICAL | A05 | api/app.py:50-57 |
| H8 | Error message leaks internal details | HIGH | A04 | All routers |
| M5 | S3 credentials fetched at init time | MEDIUM | A02 | s3_archival.py:50-56 |
| L2 | No request body size limits | LOW | A05 | FastAPI app |

---

## Performance Recommendations

### P1. Replace Per-Record InfluxDB Writes with Batch Writes

**Files**: `tiered_retention.py` (lines 106-117), `materialized_views.py` (lines 94-105), `storage_analytics.py` (line 145)

All downsampling operations write to InfluxDB one point at a time in a loop:

```python
for _, row in result.iterrows():
    point = Point("hourly_aggregates") \
        .tag("entity_id", row['entity_id']) \
        # ...
    self.client.write(point)  # One network round-trip per point!
```

**Fix**: Batch all points and write once:
```python
points = []
for _, row in result.iterrows():
    point = Point("hourly_aggregates") \
        .tag("entity_id", row['entity_id']) \
        # ...
    points.append(point)

if points:
    self.client.write(points)  # Single network call
```

### P2. `iterrows()` is Extremely Slow for DataFrames

**Files**: `tiered_retention.py`, `materialized_views.py`

`iterrows()` is the slowest way to iterate pandas DataFrames. For large datasets, use `itertuples()` or vectorized operations.

### P3. Compression with Level 9 is Excessive for Background Tasks

**File**: `data_compression.py`, lines 119, 121, 123

All compression algorithms use maximum compression level (9). Level 6 typically achieves 95%+ of the compression ratio at 2-3x faster speed.

### P4. Data Cleanup Deletes Records One-by-One

**File**: `c:\cursor\HomeIQ\services\data-retention\src\data_cleanup.py`, lines 229-244

```python
for record in records:
    try:
        await self.influxdb_client.delete(
            bucket="home-assistant-events",
            start=record["timestamp"],
            stop=record["timestamp"],
            predicate=f'_measurement="{record["measurement"]}"'
        )
```

This makes one DELETE API call per record. InfluxDB's delete API supports time ranges, so a single bulk delete call could replace thousands of individual calls.

---

## Test Coverage Analysis

### Tested Modules (5/16 source modules = 31%)

| Module | Test File | Coverage Level |
|--------|-----------|----------------|
| `main.py` | `test_main.py` | Good - 30+ tests |
| `data_cleanup.py` | `test_data_cleanup.py` | Good - 12 tests |
| `retention_policy.py` | `test_retention_policy.py` | Good - 12 tests |
| `backup_restore.py` | `test_backup_restore.py` | Good - 20+ tests |
| `api/routers/health.py` | `test_health_check.py` | Good - 25+ tests |

### Untested Modules (11/16 = 69% -- CRITICAL GAP)

| Module | Risk Level | Notes |
|--------|------------|-------|
| `data_compression.py` | HIGH | Complex logic with multiple algorithms |
| `storage_monitor.py` | HIGH | Alert threshold logic, disk usage |
| `materialized_views.py` | CRITICAL | Contains SQL injection vulnerability |
| `s3_archival.py` | HIGH | S3 operations, temp file handling |
| `storage_analytics.py` | MEDIUM | Metrics calculation |
| `tiered_retention.py` | HIGH | Core downsampling logic |
| `scheduler.py` | MEDIUM | Scheduling correctness |
| `statistics_aggregator.py` | HIGH | N+1 query, SQLite interaction |
| `pattern_aggregate_retention.py` | MEDIUM | Cleanup logic |
| `api/routers/policies.py` | LOW | Covered indirectly via test_health_check |
| `api/routers/retention.py` | HIGH | Retention operation triggers |

### Missing Test Scenarios

1. **No negative/boundary tests for API inputs**: What happens with retention_period=0, retention_period=-1, retention_period=999999?
2. **No concurrent access tests**: What if two cleanup operations run simultaneously?
3. **No integration tests with actual InfluxDB**: All InfluxDB interactions use mocks or fall through to mock implementations
4. **No tests for the scheduler**: Task scheduling, daily task deduplication, periodic tasks
5. **No tests for compression service**: Algorithm selection, performance, error handling
6. **No tests for storage monitor**: Alert creation, resolution, threshold changes
7. **No tests for S3 archival**: Archive, restore, error handling, temp file cleanup

### conftest.py Skips All Tests When influxdb_client_3 Is Missing

**File**: `c:\cursor\HomeIQ\services\data-retention\tests\conftest.py`, lines 9-13

```python
if importlib.util.find_spec("influxdb_client_3") is None:
    pytest.skip(
        "influxdb_client_3 dependency not installed; skipping data-retention tests",
        allow_module_level=True,
    )
```

This skips ALL tests if `influxdb_client_3` is not installed, even though 95% of the tests do not need it (they use mocks). This could silently disable the entire test suite in CI environments.

---

## Architecture Recommendations

### A1. Remove Dead Code and Consolidate to Single Framework

The service should commit to FastAPI and remove all aiohttp remnants:
- `health_check.py` (aiohttp handlers) -- dead code
- `retention_endpoints.py` (aiohttp handlers) -- dead code
- The `create_app()` function in `health_check.py` -- never called
- The `RetentionEndpoints` class -- instantiated but never bound to a running server

### A2. Separate Concerns: Service Orchestrator vs. Business Logic

`main.py` is doing too much: it's the service orchestrator, dependency container, API facade, AND the main entry point. Consider splitting:
- `service.py` -- DataRetentionService class (orchestration only)
- `dependencies.py` -- Dependency injection setup
- `main.py` -- Entry point (uvicorn launch only)

### A3. Use InfluxDB Tasks Instead of Application-Level Downsampling

The tiered retention (hot->warm->cold) downsampling is implemented at the application level, querying data and writing back. InfluxDB 2.x natively supports Tasks (scheduled Flux scripts) that can do this more efficiently and reliably. Consider migrating the downsampling logic to InfluxDB Tasks.

### A4. Add Proper Health Check Levels

The current health check returns "healthy", "warning", or "critical" based only on storage alerts. A comprehensive health check should also verify:
- InfluxDB connectivity
- SQLite accessibility
- Scheduler running status
- Last successful cleanup/compression time
- Memory usage

### A5. Environment Variable Validation at Startup

Critical env vars like `INFLUXDB_TOKEN` are read but never validated. The service silently runs with `None` tokens, leading to unclear failures later. Add startup validation:

```python
required_vars = ["INFLUXDB_URL", "INFLUXDB_TOKEN", "INFLUXDB_ORG"]
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    logger.error(f"Missing required environment variables: {missing}")
    sys.exit(1)
```

### A6. Add Rate Limiting to Destructive Endpoints

Endpoints like `POST /cleanup`, `POST /retention/downsample-hourly`, `POST /backup/restore` are expensive operations that should have rate limiting to prevent accidental or malicious repeated invocations.

---

## Dockerfile Review

### Strengths
- Multi-stage build separating builder from production
- Non-root user (`appuser:appgroup`)
- Layer cache optimization with `--mount=type=cache`
- Proper HEALTHCHECK directive
- `.dockerignore` properly excludes test and documentation files

### Issues Found

1. **`pip==25.2` pinned in builder** (Dockerfile line 9): This pip version may not exist yet or may be outdated. Use `pip install --upgrade pip` without version pinning for builder stage.

2. **Missing `.env` file handling**: The Dockerfile.dev does not copy `.env` files, but the application calls `load_dotenv()`. The production Dockerfile also doesn't handle environment variables -- they should come from Docker Compose or orchestrator, which is correct.

3. **Dev Dockerfile runs as root**: `Dockerfile.dev` doesn't create or switch to a non-root user. While acceptable for development, it's better practice to match production patterns.

4. **Dev Dockerfile missing shared module copy**: `Dockerfile.dev` only copies `src/` but the code imports from `shared/` (via `sys.path.append`). This would fail in the dev container:
   ```dockerfile
   # Missing:
   COPY shared/ ../shared/
   ```

---

## Dependency Review

### requirements.txt Issues
| Package | Issue |
|---------|-------|
| `asyncio-mqtt` | Not used anywhere in source code |
| `pytest`, `pytest-asyncio`, `pytest-cov` | Test deps in main requirements |
| `aiohttp` | Only used in dead code (health_check.py, retention_endpoints.py) |

### requirements-prod.txt Issues
| Package | Issue |
|---------|-------|
| `schedule==1.2.1` | Not imported anywhere in source code |
| `aiohttp` | Only used in dead code |

### Pinning Concerns
- `influxdb3-python==0.3.0` is exactly pinned -- good for reproducibility but needs regular updates
- `boto3==1.36.5` is exactly pinned -- same concern
- `pyarrow==15.0.2` is exactly pinned -- known to have frequent security updates
- `pydantic>=2.8.2` has a loose lower bound -- could break with major API changes in 2.x

---

## Summary of Recommendations by Priority

### Immediate (This Sprint)
1. Fix SQL injection in `materialized_views.py` query_view() [C1]
2. Fix Zip Slip vulnerability in backup restore [C3]
3. Fix arbitrary file write in config restore [C4]
4. Add authentication to API endpoints [C5]
5. Restrict CORS origins [C6]

### Next Sprint
6. Fix unbounded memory growth in history lists [H1]
7. Remove dead aiohttp code [H2]
8. Make compression non-blocking [H3]
9. Fix error message leaking [H8]
10. Fix SQLite connection handling [H7]

### Backlog
11. Fix deprecated `datetime.utcnow()` usage [M1]
12. Call validate_policy() during add/update [M10]
13. Remove unused dependencies [M6, L5, L6]
14. Add batch writes for InfluxDB [P1]
15. Add missing test coverage for 11 untested modules
16. Batch aggregation queries in statistics_aggregator [H6]

---

*End of Review*
