# Blueprint Index Service - Deep Code Review

**Service**: blueprint-index (Tier 7 - Specialized Service)
**Port**: 8031 (internal) / 8038 (external)
**Purpose**: Indexes and searches Home Assistant community blueprints from GitHub and Discourse forums
**Review Date**: 2026-02-06
**Reviewer**: Claude Opus 4.6

---

## Service Overview

The Blueprint Index Service crawls GitHub repositories and Home Assistant Community Discourse forums to build a searchable index of Home Assistant blueprints. It provides APIs for searching by device domain, device class, trigger/action patterns, text queries, and quality scores. The service uses SQLite (via aiosqlite/SQLAlchemy async) for storage and httpx for async HTTP requests to external APIs.

**Architecture Components**:
- `src/main.py` - FastAPI application with CORS, lifespan, health check
- `src/config.py` - Pydantic settings from environment variables
- `src/database.py` - SQLAlchemy async engine, session management
- `src/models/blueprint.py` - IndexedBlueprint, BlueprintInput, IndexingJob models
- `src/api/routes.py` - REST API endpoints (search, pattern match, indexing)
- `src/api/schemas.py` - Pydantic request/response schemas
- `src/indexer/blueprint_parser.py` - YAML blueprint parser and metadata extractor
- `src/indexer/github_indexer.py` - GitHub API crawler
- `src/indexer/discourse_indexer.py` - Discourse API crawler
- `src/indexer/index_manager.py` - Indexing job orchestration
- `src/search/search_engine.py` - Database search and filtering
- `src/search/ranking.py` - Blueprint ranking algorithms

---

## Findings

### CRITICAL Severity

#### C1. YAML Unsafe Deserialization via Global Loader Mutation
**File**: `src/indexer/blueprint_parser.py:23`
```python
yaml.add_constructor('!input', _input_constructor, Loader=yaml.SafeLoader)
```
**Issue**: This globally mutates the `yaml.SafeLoader` class by adding a custom constructor. This is a process-wide side effect that persists for the lifetime of the application. While `!input` itself is benign, the pattern of mutating a global loader class is dangerous:
1. Any other code in the process using `yaml.safe_load()` will now silently handle `!input` tags instead of raising an error.
2. If another service or library adds additional constructors to SafeLoader, they accumulate globally.
3. This is not thread-safe during the registration itself.

**Fix**: Create a dedicated loader subclass instead of mutating the global SafeLoader:
```python
class BlueprintSafeLoader(yaml.SafeLoader):
    """Custom YAML loader that handles !input tags."""
    pass

BlueprintSafeLoader.add_constructor('!input', _input_constructor)
```
Then use `yaml.load(yaml_content, Loader=BlueprintSafeLoader)` instead of `yaml.safe_load()`.

---

#### C2. CORS Wildcard with Credentials Enabled
**File**: `src/main.py:64-70`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),  # Returns ["*"] by default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Issue**: Setting `allow_origins=["*"]` with `allow_credentials=True` is a security vulnerability. The CORS spec explicitly forbids this combination. While FastAPI/Starlette handles this by not sending `Access-Control-Allow-Credentials` when the origin is `*`, the intent here is clearly wrong and the comment on line 56 even acknowledges the issue but leaves it as a "development default." A production deployment could easily miss configuring `CORS_ORIGINS`.

**Fix**: Set `allow_credentials=False` when using wildcard origins, or require explicit origin configuration:
```python
cors_origins = _get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

#### C3. Unprotected Indexing Endpoint - No Authentication
**File**: `src/api/routes.py:166-204`
```python
@router.post("/index/refresh", response_model=IndexingJobResponse)
async def trigger_indexing(
    request: TriggerIndexingRequest,
    db: AsyncSession = Depends(get_db)
):
```
**Issue**: The `POST /api/blueprints/index/refresh` endpoint triggers a potentially long-running indexing job that makes many external API requests (GitHub, Discourse). There is zero authentication or authorization. Any anonymous client can trigger indexing, which:
1. Consumes GitHub API rate limits (especially without a token).
2. Creates database load storing/updating blueprints.
3. Can be used for denial-of-service by repeatedly triggering jobs.

**Fix**: Add authentication middleware or an API key check:
```python
from fastapi import Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post("/index/refresh", response_model=IndexingJobResponse, dependencies=[Depends(verify_api_key)])
```

---

### HIGH Severity

#### H1. SQL Injection via Dynamic Sort Column
**File**: `src/search/search_engine.py:126`
```python
sort_column = getattr(IndexedBlueprint, request.sort_by, IndexedBlueprint.quality_score)
```
**Issue**: The `sort_by` parameter is user-supplied via the query string and used with `getattr()` to access arbitrary attributes on the `IndexedBlueprint` model. While SQLAlchemy prevents raw SQL injection, this allows:
1. Sorting by unintended internal fields (e.g., `yaml_content`, `__tablename__`).
2. Potential information leakage or errors from accessing non-column attributes.

**Fix**: Whitelist allowed sort fields:
```python
ALLOWED_SORT_FIELDS = {"quality_score", "community_rating", "stars", "name", "created_at", "updated_at"}

sort_field = request.sort_by if request.sort_by in ALLOWED_SORT_FIELDS else "quality_score"
sort_column = getattr(IndexedBlueprint, sort_field)
```

---

#### H2. Fire-and-Forget Background Task with No Error Recovery
**File**: `src/indexer/index_manager.py:71`
```python
asyncio.create_task(self._run_indexing_job(job.id, job_type))
```
**Issue**: The indexing job is launched as an untracked `asyncio.create_task()`. Problems:
1. If the task raises an unhandled exception, it silently fails (only logged as a "Task exception was never retrieved" warning).
2. The task is not stored in any reference, so it can be garbage collected.
3. There is no cancellation mechanism - `cancel_job()` only updates the DB status but the actual background task keeps running.
4. If the app shuts down (lifespan shutdown), running indexing tasks are not awaited or cancelled gracefully.

**Fix**: Store and track background tasks; add cancellation support:
```python
class IndexManager:
    _running_tasks: dict[str, asyncio.Task] = {}

    async def start_indexing_job(self, ...):
        ...
        task = asyncio.create_task(self._run_indexing_job(job.id, job_type))
        task.add_done_callback(lambda t: self._running_tasks.pop(job.id, None))
        self._running_tasks[job.id] = task
        return job

    async def cancel_job(self, job_id: str) -> bool:
        task = self._running_tasks.get(job_id)
        if task:
            task.cancel()
        ...
```

---

#### H3. `_classify_use_case` Converts Entire YAML Data to String
**File**: `src/indexer/blueprint_parser.py:341`
```python
text = f"{name} {description} {str(yaml_data)}".lower()
```
**Issue**: `str(yaml_data)` converts the entire parsed YAML structure (which can be very large for complex blueprints) to a string for keyword matching. This is:
1. **Extremely inefficient** - O(n) where n is the serialized size of the YAML.
2. **Produces false positives** - Keywords in entity IDs, service names, or arbitrary values get matched (e.g., `light` in `light.turn_on` matches "comfort" category).
3. **Memory wasteful** - Creates a potentially huge string for each blueprint parsed.

**Fix**: Restrict keyword matching to name and description only, plus targeted field extraction:
```python
def _classify_use_case(self, name: str, description: str, yaml_data: dict[str, Any]) -> str:
    text = f"{name} {description}".lower()
    # Optionally include tags if present
    tags = yaml_data.get('blueprint', {}).get('tags', [])
    if tags:
        text += " " + " ".join(str(t) for t in tags)
    ...
```

---

#### H4. Missing `sort_order` Validation
**File**: `src/api/routes.py:62`
```python
sort_order: str = Query(default="desc"),
```
**Issue**: `sort_order` accepts any string. Invalid values like `sort_order=DROP_TABLE` would pass validation. While SQLAlchemy prevents actual SQL injection, the search engine code at `search_engine.py:127` only checks for `"desc"`, meaning any non-`"desc"` value silently becomes `"asc"`. This is confusing behavior.

**Fix**: Use an enum or literal validation:
```python
sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
```
Or use a Pydantic `Literal`:
```python
from typing import Literal
sort_order: Literal["asc", "desc"] = Query(default="desc"),
```

---

#### H5. `job_type` Validation Missing
**File**: `src/api/schemas.py:183`
```python
job_type: str = Field(default="full", description="Type of indexing job: 'github', 'discourse', 'full'")
```
**Issue**: `job_type` accepts any string but only `"github"`, `"discourse"`, and `"full"` are valid. An invalid `job_type` (e.g., `"drop_tables"`) would create a job that does nothing but be marked as completed, wasting resources and confusing the status.

**Fix**: Use a Literal or Enum:
```python
job_type: Literal["github", "discourse", "full"] = Field(default="full")
```

---

### MEDIUM Severity

#### M1. Duplicate Health Check Endpoints
**File**: `src/main.py:86-89` and `src/api/routes.py:28-31`
```python
# main.py
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name}

# routes.py
@router.get("/health")  # Becomes /api/blueprints/health
async def health_check():
    return {"status": "healthy", "service": "blueprint-index"}
```
**Issue**: Two health check endpoints exist: `/health` (main.py) and `/api/blueprints/health` (routes.py). The Docker HEALTHCHECK uses `/health`. The one in routes.py is redundant, uses a hardcoded service name instead of `settings.service_name`, and neither checks actual health (database connectivity, etc.).

**Fix**: Remove the duplicate in `routes.py`. Enhance the `/health` endpoint in `main.py` to check database connectivity:
```python
@app.get("/health")
async def health():
    try:
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": settings.service_name}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unhealthy")
```

---

#### M2. Deprecated `asyncio.get_event_loop()` Usage
**Files**: `src/indexer/github_indexer.py:100,107` and `src/indexer/discourse_indexer.py:73,80`
```python
current_time = asyncio.get_event_loop().time()
```
**Issue**: `asyncio.get_event_loop()` is deprecated in Python 3.10+ and raises a DeprecationWarning if no event loop is running. The correct modern API is `asyncio.get_running_loop()`.

**Fix**:
```python
current_time = asyncio.get_running_loop().time()
```

---

#### M3. Rate Limiter Silently Drops Requests on 429
**File**: `src/indexer/discourse_indexer.py:101-103`
```python
elif response.status_code == 429:
    logger.warning(f"Rate limited: {url}")
    await asyncio.sleep(60)
    return {}
```
**Issue**: When rate-limited (429 or 403 for GitHub), the request is silently dropped after sleeping - no retry is attempted. The caller receives an empty dict and the blueprint for that topic is simply skipped. Same issue in `github_indexer.py:128-130`.

**Fix**: Implement retry logic:
```python
async def _request(self, method, endpoint, params=None, retries=3):
    for attempt in range(retries):
        ...
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limited, retry in {retry_after}s (attempt {attempt+1}/{retries})")
            await asyncio.sleep(retry_after)
            continue
        ...
    return {}  # All retries exhausted
```

---

#### M4. `inputs_raw` Type Not Validated in `_extract_inputs`
**File**: `src/indexer/blueprint_parser.py:190-193`
```python
def _extract_inputs(self, inputs_raw: dict[str, Any]) -> tuple[...]:
    ...
    for input_name, input_def in inputs_raw.items():
```
**Issue**: `inputs_raw` comes from `blueprint_meta.get('input', {})` which could return any type (e.g., a string, list, or None if the YAML is malformed). Calling `.items()` on a non-dict will raise `AttributeError`. The caller at line 115 does `inputs_raw = blueprint_meta.get('input', {})` which can return a non-dict if `input:` is set to a string or list in the YAML.

**Fix**: Add a type guard:
```python
def _extract_inputs(self, inputs_raw):
    if not isinstance(inputs_raw, dict):
        return {}, [], set()
    ...
```

---

#### M5. Hardcoded GitHub URL Assumption
**File**: `src/indexer/github_indexer.py:264`
```python
"url": f"https://github.com/{owner}/{repo}/blob/main/{item_path}",
```
**Issue**: The URL always assumes the default branch is `main`. Many repositories use `master` or other branch names. This produces broken URLs for those repositories.

**Fix**: Fetch the default branch from the repository metadata:
```python
default_branch = repo_data.get("default_branch", "main")
# Then use:
"url": f"https://github.com/{owner}/{repo}/blob/{default_branch}/{item_path}",
```

---

#### M6. `search_blueprints` and `search_code` Methods Are Unused
**Files**: `src/indexer/discourse_indexer.py:275-315`, `src/indexer/github_indexer.py:335-367`

**Issue**: The `search_blueprints()` method in DiscourseBlueprintIndexer and `search_code()` in GitHubBlueprintIndexer are defined but never called anywhere in the codebase. They are dead code.

**Fix**: Either remove them or wire them into an API endpoint if needed.

---

#### M7. No Request Size Limits on Indexing Input
**File**: `src/api/routes.py:166-204`

**Issue**: The `TriggerIndexingRequest` body has no validation on `job_type` beyond being a string (noted in H5), but more importantly, the indexing process has no bounds checking. A "full" index job fetches up to `50 pages * N topics` from Discourse plus crawls all repositories recursively. There is no timeout, maximum blueprint count, or resource limit on a single job.

**Fix**: Add configurable limits:
```python
# In config.py
max_discourse_pages: int = 50
max_github_repos: int = 100
indexing_timeout_minutes: int = 60
```

---

#### M8. f-string in Logging Statements
**Files**: Multiple locations throughout the codebase (e.g., `main.py:33`, `routes.py:45,99,138`, etc.)
```python
logger.error(f"Search failed: {e}", exc_info=True)
```
**Issue**: Using f-strings in logging calls means the string is always formatted, even if the log level would suppress the message. This has a minor performance cost and goes against Python logging best practices.

**Fix**: Use lazy formatting:
```python
logger.error("Search failed: %s", e, exc_info=True)
```

---

#### M9. `updated_at` Column Never Updated on Record Changes
**File**: `src/models/blueprint.py:88`
```python
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```
**Issue**: `updated_at` is set at creation time via `default=` but has no `onupdate=` handler. When an existing blueprint is updated during re-indexing (index_manager.py:134), the `updated_at` field from the source data is used, but if that is `None`, the field remains at its original creation value.

**Fix**: Add `onupdate`:
```python
updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

---

### LOW Severity

#### L1. Duplicate `httpx` Entry in `requirements.txt`
**File**: `requirements.txt:17,28`
```
httpx>=0.26.0   # line 17
httpx>=0.26.0   # line 28
```
**Issue**: `httpx` is listed twice in requirements.txt - once under HTTP client and again under Testing. While not breaking, it is messy.

**Fix**: Remove the duplicate entry on line 28.

---

#### L2. Dev/Test Dependencies Mixed with Production
**File**: `requirements.txt:24-33`
```
# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0

# Development
black>=24.1.0
ruff>=0.1.14
mypy>=1.8.0
```
**Issue**: Test and development dependencies (pytest, black, ruff, mypy) are in the same `requirements.txt` as production dependencies. The Dockerfile installs all of them into the production image, increasing image size unnecessarily.

**Fix**: Split into `requirements.txt` (production) and `requirements-dev.txt` (dev/test):
```
# requirements-dev.txt
-r requirements.txt
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
black>=24.1.0
ruff>=0.1.14
mypy>=1.8.0
```

---

#### L3. `python-json-logger` Listed but Never Used
**File**: `requirements.txt:22`
```
python-json-logger>=2.0.7
```
**Issue**: `python-json-logger` is in requirements but the logging configuration in `main.py:17-21` uses a simple `StreamHandler` with a plain text format. Structured JSON logging is never configured.

**Fix**: Either remove the dependency or implement structured JSON logging for production.

---

#### L4. Port Mismatch in Docker Compose External Mapping
**File**: `docker-compose.yml:1676`
```yaml
ports:
  - "8038:8031"  # External 8038, internal 8031
```
**Issue**: The README documents port 8031 as the service port, but docker-compose maps it externally to 8038. Other HomeIQ services (e.g., `blueprint-suggestion-service`) reference it as `http://blueprint-index:8031` (internal), which is correct. However, external access uses 8038, which is undocumented in the README.

**Fix**: Document the external port mapping in the README's Docker section.

---

#### L5. No Version Pinning in requirements.txt
**File**: `requirements.txt`
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.25
```
**Issue**: All dependencies use `>=` (minimum version) with no upper bound. A `pip install` could pull in a breaking major version (e.g., FastAPI 1.0, SQLAlchemy 3.0). This can cause unexpected breakage in production.

**Fix**: Use compatible release specifiers or pin specific versions:
```
fastapi>=0.109.0,<1.0.0
sqlalchemy[asyncio]>=2.0.25,<3.0.0
```

---

#### L6. Rollback Shell Scripts Left in Repository Root
**Files**: `rollback_pytest_asyncio_20260205_140814.sh`, `rollback_pytest_asyncio_20260205_143708.sh`

**Issue**: Two rollback scripts from pytest-asyncio migration are left in the service directory. These are development artifacts and should not be in the repository.

**Fix**: Remove both files and add them to `.gitignore`.

---

#### L7. `__pycache__` and `.ruff_cache` in Repository
**Files**: Multiple `__pycache__` and `.ruff_cache` directories

**Issue**: Compiled Python bytecode files and ruff cache are present in the repository tree. These should be in `.gitignore`.

**Fix**: Add to `.gitignore`:
```
__pycache__/
*.pyc
.ruff_cache/
```

---

#### L8. `BlueprintInput` Model Defined but Never Populated
**File**: `src/models/blueprint.py:138-173`

**Issue**: The `BlueprintInput` model with its `inputs_rel` relationship on `IndexedBlueprint` is fully defined, but the indexer never creates `BlueprintInput` records. The parser extracts inputs into the JSON `inputs` column on `IndexedBlueprint` but never populates the normalized `blueprint_inputs` table.

**Fix**: Either implement input population in the parser or remove the unused model/relationship to reduce dead code.

---

#### L9. `import math` Inside Function Body
**File**: `src/indexer/blueprint_parser.py:409`
```python
if stars > 0:
    import math
    star_score = min(0.4, (math.log10(stars + 1) / 3) * 0.4)
```
**Issue**: The `math` module is imported conditionally inside `_calculate_quality_score()`. This is a standard library module with negligible import cost. Inline imports hurt readability and cause repeated import overhead on each call.

**Fix**: Move to top-level imports:
```python
import math  # At the top of the file
```

---

#### L10. Conftest Uses Deprecated `event_loop` Fixture Pattern
**File**: `tests/conftest.py:12-17`
```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```
**Issue**: The `event_loop` fixture pattern is deprecated in `pytest-asyncio >= 0.21`. The recommended approach is to use the `loop_scope` configuration via `pytest.ini` or `pyproject.toml`.

**Fix**: Remove the `event_loop` fixture and configure in `pyproject.toml`:
```toml
[tool.pytest-asyncio]
mode = "auto"
```

---

## Missing Test Coverage

| Component | Covered | Missing |
|-----------|---------|---------|
| `blueprint_parser.py` | Good - 14 tests | Edge cases: empty YAML, huge inputs, nested selectors, multi-domain selectors |
| `ranking.py` | Good - 8 tests | Edge cases: empty lists, None fields, negative scores |
| `search_engine.py` | Good - 11 tests | Edge cases: SQL injection in sort_by, concurrent searches, empty database |
| `routes.py` | None | All API route tests missing (should use FastAPI TestClient) |
| `index_manager.py` | None | All indexing job orchestration tests missing |
| `github_indexer.py` | None | All GitHub crawling tests missing (mock httpx) |
| `discourse_indexer.py` | None | All Discourse crawling tests missing (mock httpx) |
| `database.py` | Indirect | Direct session lifecycle tests missing |
| `main.py` | None | App startup/shutdown, CORS, root endpoint tests missing |

**Key testing gaps**: The indexer modules (GitHub, Discourse, IndexManager) have zero test coverage. These are the most critical components for data quality and reliability.

---

## Prioritized Action Plan

### Phase 1: Security Fixes (Immediate)
1. **C1** - Fix YAML loader global mutation (create subclass)
2. **C2** - Fix CORS wildcard + credentials conflict
3. **C3** - Add authentication to indexing endpoint
4. **H1** - Whitelist sort_by fields
5. **H4** - Validate sort_order to asc/desc
6. **H5** - Validate job_type to enum/literal

### Phase 2: Reliability Fixes (This Sprint)
7. **H2** - Track background tasks, add cancellation support
8. **M3** - Implement retry logic for rate-limited requests
9. **M4** - Add type guard for `_extract_inputs` parameter
10. **M5** - Fix hardcoded `main` branch assumption
11. **M9** - Add `onupdate` to `updated_at` column

### Phase 3: Code Quality (Next Sprint)
12. **H3** - Restrict `_classify_use_case` to name/description only
13. **M1** - Remove duplicate health endpoint, add DB health check
14. **M2** - Replace deprecated `get_event_loop()` with `get_running_loop()`
15. **M8** - Convert f-string logging to lazy formatting
16. **L1** - Remove duplicate httpx in requirements
17. **L2** - Split production and dev requirements
18. **L3** - Remove unused python-json-logger or implement JSON logging
19. **L5** - Add upper bound version constraints

### Phase 4: Cleanup and Tests
20. **L6** - Remove rollback scripts
21. **L7** - Add __pycache__/.ruff_cache to .gitignore
22. **L8** - Remove unused BlueprintInput model or implement population
23. **L9** - Move `import math` to top level
24. **L10** - Update conftest to modern pytest-asyncio pattern
25. **M6** - Remove dead code (unused search methods) or wire them in
26. Write integration tests for routes using FastAPI TestClient
27. Write unit tests for indexer modules with mocked HTTP clients
28. Write tests for IndexManager job lifecycle

---

## Enhancement Suggestions

### 1. Full-Text Search Index
The current text search uses `LIKE %query%` which does not scale. Consider using SQLite FTS5 for proper full-text search capabilities.

### 2. Caching Layer
Blueprint search results are queried from the database on every request. Add an in-memory cache (e.g., `cachetools.TTLCache`) for frequently searched patterns.

### 3. Webhook/Scheduled Indexing
Currently indexing is only triggered via API. Add a configurable scheduler (e.g., `apscheduler`) for periodic re-indexing based on `index_refresh_interval_hours`.

### 4. Metrics and Observability
No Prometheus metrics or OpenTelemetry tracing. Add counters for:
- Search request count/latency
- Indexing job duration/success rate
- External API call count/failure rate

### 5. Pagination Cursor
Current offset-based pagination is inefficient for large datasets. Consider cursor-based pagination using `indexed_at` or `id` as the cursor.

### 6. Rate Limit on Search API
The search endpoint has no rate limiting. A malicious client could overload the database with expensive queries. Add rate limiting middleware.
