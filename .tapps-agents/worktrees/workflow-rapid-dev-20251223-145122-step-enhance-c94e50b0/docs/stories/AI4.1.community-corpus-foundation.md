# Story AI4.1: Community Corpus Foundation

**Epic:** AI-4 (Community Knowledge Augmentation)  
**Status:** InProgress  
**Created:** October 18, 2025  
**Estimated Effort:** 3-4 days  

---

## Story

**As a** Home Assistant user,  
**I want** the system to crawl high-quality Home Assistant community automations,  
**so that** I receive suggestions backed by proven, community-validated automation ideas.

---

## Acceptance Criteria

### Functional Requirements

1. **Selective Discourse Crawler** [[memory:10045893]]
   - Crawler fetches automations from community.home-assistant.io Blueprints Exchange (category 53)
   - Only fetches posts with 500+ likes (high-quality threshold)
   - Parses post content, metadata (title, author, votes, tags, created/updated dates)
   - Respects rate limits (2 requests/second)
   - Handles pagination for 2,000-3,000 posts

2. **GitHub Blueprint Crawler** (Optional for v1)
   - Fetches repos tagged `home-assistant-blueprint` with 50+ stars
   - Parses README for automation description and metadata
   - Extracts YAML blueprint structure

3. **Normalization Pipeline**
   - Parses automation YAML or description text
   - Extracts structured metadata:
     - Device/integration names (normalized)
     - Trigger types (time, state, event, etc.)
     - Condition types (optional)
     - Action types
     - Complexity score (low/medium/high)
     - Use case tags (security, comfort, energy, convenience)
   - Removes PII and instance-specific data (entity IDs, IP addresses)
   - Quality score calculation (0.0-1.0 based on votes, recency, completeness)

4. **SQLite Storage Schema**
   - Table: `community_automations`
     - id (INTEGER PRIMARY KEY)
     - source (TEXT: 'discourse', 'github')
     - source_id (TEXT: post ID or repo URL)
     - title (TEXT)
     - description (TEXT: normalized, no PII)
     - devices (JSON: `["light", "motion_sensor", "switch"]`)
     - integrations (JSON: `["mqtt", "zigbee2mqtt", "hue"]`)
     - triggers (JSON: `[{"type": "time", "pattern": "sunset"}]`)
     - conditions (JSON)
     - actions (JSON: `[{"device": "light", "action": "turn_on"}]`)
     - use_case (TEXT: 'energy' | 'comfort' | 'security' | 'convenience')
     - complexity (TEXT: 'low' | 'medium' | 'high')
     - quality_score (REAL: 0.0-1.0)
     - vote_count (INTEGER)
     - created_at (TEXT: ISO 8601)
     - updated_at (TEXT: ISO 8601)
     - last_crawled (TEXT: ISO 8601)
     - metadata (JSON: extra data)
   - Indexes: devices, integrations, use_case, quality_score, source

5. **Query API Endpoints**
   - `GET /api/automation-miner/corpus/search` - Query by device/integration/use_case
     - Query params: `device`, `integration`, `use_case`, `min_quality`, `limit`
     - Returns: List of matching automations
   - `GET /api/automation-miner/corpus/stats` - Corpus statistics
     - Returns: Total count, avg quality, device coverage, integration coverage
   - `GET /api/automation-miner/corpus/{id}` - Get single automation details

### Integration Requirements

6. **Existing Phase 1 Unaffected**
   - All crawlers run as background tasks (APScheduler)
   - No blocking of existing daily AI analysis (3 AM job)
   - Graceful degradation: If crawler fails, Phase 1 suggestions continue unchanged
   - Feature flag: `ENABLE_AUTOMATION_MINER` (default: false for v1)

7. **Database Integration**
   - New tables created via SQLAlchemy migrations
   - No modifications to existing `ai_automation.db` schema
   - Corpus stored in same database (isolated tables)
   - Connection pooling compatible with existing async sessions

### Quality Requirements

8. **Corpus Quality Targets**
   - 2,000+ automations in initial crawl
   - Average quality score ≥ 0.7
   - 50+ unique device types covered
   - 30+ integrations covered
   - Deduplication: <5% duplicate entries (by normalized title + devices)

9. **Performance**
   - Initial crawl: <3 hours total
   - Query API: <100ms p95 response time
   - Storage: <500MB database size
   - Crawler memory: <200MB

10. **Error Handling & Logging**
    - Retry logic for failed HTTP requests (3 attempts, exponential backoff)
    - Structured logging with correlation IDs
    - Health check: `/health` includes miner status (`corpus_count`, `last_crawl_time`)
    - Alert if crawler fails 3 consecutive times

---

## Tasks / Subtasks

### Task 1: Setup Project Structure (AC: 6, 7)
- [x] Create `services/automation-miner/` directory structure
  - [x] `src/miner/` (crawler, parser, storage modules)
  - [x] `src/api/` (FastAPI endpoints)
  - [x] `tests/` (unit + integration tests)
  - [x] `alembic/` (database migrations)
- [x] Create `requirements.txt` with Context7-validated dependencies [[memory:10014278]]:
  - `httpx>=0.27.0` (async HTTP with retry)
  - `beautifulsoup4>=4.12.0` (HTML parsing)
  - `pydantic>=2.8.0` (data validation)
  - `fastapi>=0.115.0` (API framework)
  - `sqlalchemy[asyncio]>=2.0.0` (async ORM)
  - `apscheduler>=3.10.0` (job scheduling)
  - `pyyaml>=6.0` (YAML parsing)
  - `rapidfuzz>=3.0.0` (deduplication)
- [x] Add Dockerfile and docker-compose config (port 8019)

### Task 2: Implement Discourse Crawler (AC: 1, 9, 10)
- [x] Create `DiscourseClient` class using `httpx.AsyncClient`
  - [x] Implement retry logic (3 attempts, exponential backoff) [Context7: httpx retry]
  - [x] Configure timeouts (connect: 10s, read: 30s) [Context7: httpx timeout]
  - [x] Rate limiting (2 requests/second)
  - [x] Connection pooling (max 10 connections) [Context7: httpx limits]
- [x] Implement `fetch_blueprints()` method
  - [x] Query `/c/blueprints-exchange/53.json` with pagination
  - [x] Filter by likes ≥ 500
  - [x] Parse JSON response to extract post metadata
  - [x] Handle API errors (404, 429, 500) with graceful degradation
- [x] Implement `fetch_post_details(post_id)` method
  - [x] Fetch full post content (including YAML blueprint if present)
  - [x] Extract code blocks (```yaml ... ```)
  - [x] Parse BeautifulSoup for formatted content
- [x] Add structured logging with correlation IDs

### Task 3: Implement Normalization Pipeline (AC: 3, 8)
- [ ] Create Pydantic models for validation [Context7: pydantic BaseModel]:
  ```python
  class AutomationMetadata(BaseModel):
      title: str = Field(min_length=5, max_length=200)
      description: str
      devices: List[str] = Field(default_factory=list)
      integrations: List[str] = Field(default_factory=list)
      triggers: List[Dict[str, Any]] = Field(default_factory=list)
      conditions: List[Dict[str, Any]] = Field(default_factory=list)
      actions: List[Dict[str, Any]] = Field(default_factory=list)
      use_case: Literal['energy', 'comfort', 'security', 'convenience']
      complexity: Literal['low', 'medium', 'high']
      quality_score: Annotated[float, Field(ge=0.0, le=1.0)]
      vote_count: int = 0
      
      @field_validator('devices')
      @classmethod
      def normalize_devices(cls, v: List[str]) -> List[str]:
          """Normalize device names (lowercase, remove spaces)"""
          return [device.lower().replace(' ', '_') for device in v]
  ```
- [ ] Create `AutomationParser` class
  - [ ] `parse_yaml(yaml_str)` - Extract YAML automation structure
  - [ ] `extract_devices(automation)` - Identify device types
  - [ ] `extract_integrations(automation)` - Identify HA integrations
  - [ ] `classify_use_case(automation)` - ML-free classification (keyword-based)
  - [ ] `calculate_complexity(automation)` - Count triggers + conditions + actions
  - [ ] `calculate_quality_score(votes, age_days, completeness)` - Weighted formula
- [ ] Implement PII removal
  - [ ] Regex to remove entity IDs (`light.bedroom_lamp` → `light`)
  - [ ] Remove IP addresses
  - [ ] Remove personal names (optional, basic pattern matching)
- [ ] Implement deduplication logic
  - [ ] Calculate similarity hash (title + devices)
  - [ ] Use `rapidfuzz` for fuzzy title matching (>85% similar = duplicate)
  - [ ] Keep higher quality score when duplicates found

### Task 4: Implement SQLite Storage (AC: 4, 7)
- [ ] Create SQLAlchemy async models
  ```python
  class CommunityAutomation(Base):
      __tablename__ = "community_automations"
      
      id = Column(Integer, primary_key=True)
      source = Column(String(20), nullable=False, index=True)
      source_id = Column(String(200), nullable=False, unique=True)
      title = Column(String(200), nullable=False)
      description = Column(Text, nullable=False)
      devices = Column(JSON, nullable=False, default=list)
      integrations = Column(JSON, nullable=False, default=list)
      triggers = Column(JSON, nullable=False, default=list)
      conditions = Column(JSON, nullable=True, default=list)
      actions = Column(JSON, nullable=False, default=list)
      use_case = Column(String(20), nullable=False, index=True)
      complexity = Column(String(10), nullable=False)
      quality_score = Column(Float, nullable=False, index=True)
      vote_count = Column(Integer, nullable=False, default=0)
      created_at = Column(DateTime, nullable=False)
      updated_at = Column(DateTime, nullable=False)
      last_crawled = Column(DateTime, nullable=False)
      metadata = Column(JSON, nullable=True)
      
      __table_args__ = (
          Index('ix_devices_gin', devices, postgresql_using='gin'),
          Index('ix_integrations_gin', integrations, postgresql_using='gin'),
      )
  ```
- [ ] Create Alembic migration for schema
- [ ] Implement `CorpusRepository` class
  - [ ] `async def save_automation(automation: AutomationMetadata)` - Insert or update
  - [ ] `async def get_by_id(id: int)` - Fetch single automation
  - [ ] `async def search(filters: Dict)` - Query with filters
  - [ ] `async def get_stats()` - Corpus statistics
  - [ ] Use async session management [Context7: SQLAlchemy async]

### Task 5: Implement Query API (AC: 5, 9)
- [ ] Create FastAPI router `/api/automation-miner/corpus`
- [ ] Implement `GET /search` endpoint
  ```python
  @router.get("/search")
  async def search_corpus(
      device: Optional[str] = None,
      integration: Optional[str] = None,
      use_case: Optional[str] = None,
      min_quality: float = 0.7,
      limit: int = 50,
      db: AsyncSession = Depends(get_db_session)
  ):
      """Search community automation corpus"""
      repo = CorpusRepository(db)
      results = await repo.search({
          'device': device,
          'integration': integration,
          'use_case': use_case,
          'min_quality': min_quality,
          'limit': limit
      })
      return {"automations": results, "count": len(results)}
  ```
- [ ] Implement `GET /stats` endpoint
- [ ] Implement `GET /{id}` endpoint
- [ ] Add OpenAPI documentation
- [ ] Performance: Cache query results (5 min TTL)

### Task 6: Implement Initial Crawl Job (AC: 1, 6, 8)
- [ ] Create `InitialCrawlJob` class
  ```python
  async def run_initial_crawl():
      """Initial corpus population (runs once)"""
      logger.info("Starting initial corpus crawl...")
      
      client = DiscourseClient()
      parser = AutomationParser()
      repo = CorpusRepository(db)
      
      # Fetch blueprints
      posts = await client.fetch_blueprints(min_likes=500, limit=3000)
      
      # Process in batches of 50
      for batch in chunks(posts, 50):
          automations = []
          for post in batch:
              try:
                  # Fetch full post
                  details = await client.fetch_post_details(post['id'])
                  
                  # Parse and normalize
                  metadata = parser.parse_automation(details)
                  
                  # Deduplicate
                  if not await repo.is_duplicate(metadata):
                      automations.append(metadata)
                      
              except Exception as e:
                  logger.error(f"Failed to process post {post['id']}: {e}")
                  continue
          
          # Bulk insert batch
          await repo.save_batch(automations)
          logger.info(f"Saved batch: {len(automations)} automations")
      
      # Log final stats
      stats = await repo.get_stats()
      logger.info(f"✅ Initial crawl complete: {stats}")
  ```
- [ ] Add manual trigger via CLI: `python -m miner.cli crawl --initial`
- [ ] Add health check integration

### Task 7: Testing & Documentation (AC: All)
- [ ] Unit tests for crawler (mock httpx responses)
- [ ] Unit tests for parser (various YAML formats)
- [ ] Unit tests for deduplication
- [ ] Integration test: Full crawl → parse → store → query
- [ ] Performance test: Query API under load (100 concurrent requests)
- [ ] Update call tree documentation (add Automation Miner flow)
- [ ] API documentation (OpenAPI/Swagger)

---

## Dev Notes

### Context from Architecture Docs

**Source Tree** (from `docs/architecture/source-tree.md`):
```
services/
├─ automation-miner/         # NEW - Community knowledge crawler
│  ├─ src/
│  │  ├─ miner/              # Crawler + parser logic
│  │  │  ├─ __init__.py
│  │  │  ├─ discourse_client.py   # Discourse API wrapper
│  │  │  ├─ github_client.py      # GitHub API wrapper (optional)
│  │  │  ├─ parser.py              # YAML → structured metadata
│  │  │  ├─ normalizer.py          # PII removal, deduplication
│  │  │  └─ repository.py          # SQLAlchemy models + queries
│  │  ├─ api/                # FastAPI endpoints
│  │  │  ├─ __init__.py
│  │  │  ├─ main.py          # FastAPI app
│  │  │  └─ routes.py        # Query endpoints
│  │  └─ cli.py              # CLI for manual crawl trigger
│  ├─ tests/
│  ├─ alembic/               # Database migrations
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ README.md
```

**Tech Stack** (from `docs/architecture/tech-stack.md`):
- Python 3.11 [[memory:10014278]]
- FastAPI 0.115+ (async web framework)
- SQLAlchemy 2.0+ (async ORM)
- httpx 0.27+ (async HTTP client)
- Pydantic 2.8+ (data validation)
- APScheduler 3.10+ (job scheduling)

**Coding Standards** (from `docs/architecture/coding-standards.md`):
- Async/await: All I/O operations must be async
- Type hints: Required for all function signatures
- Error handling: Use `try/except` with specific exceptions, log errors
- Logging: Structured logging with correlation IDs
- Database sessions: Use `async with get_db_session() as db:` pattern
- Testing: pytest-asyncio for async tests

### Context7-Validated Best Practices [[memory:10014278]]

**httpx Async Client** (from Context7):
```python
import httpx
from httpx import AsyncClient, Timeout, Limits

# Best practice: Reusable client with retry + timeout + connection pooling
transport = httpx.AsyncHTTPTransport(retries=3)
timeout = Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
limits = Limits(max_keepalive_connections=5, max_connections=10)

async with AsyncClient(
    transport=transport,
    timeout=timeout,
    limits=limits,
    headers={"User-Agent": "homeiq/1.0"}
) as client:
    response = await client.get("https://community.home-assistant.io/...")
    response.raise_for_status()
    return response.json()
```

**Pydantic Data Validation** (from Context7):
```python
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Dict, Any

class AutomationMetadata(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    devices: List[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0)
    
    @field_validator('devices')
    @classmethod
    def normalize_devices(cls, v: List[str]) -> List[str]:
        return [d.lower().replace(' ', '_') for d in v]

# Usage with error handling
try:
    automation = AutomationMetadata(**raw_data)
except ValidationError as e:
    logger.error(f"Validation failed: {e.errors()}")
    raise
```

**APScheduler Async Jobs** (from Context7):
```python
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger

async def main():
    async with AsyncScheduler() as scheduler:
        # Weekly crawl (Sunday 2 AM)
        await scheduler.add_schedule(
            weekly_corpus_refresh,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id="weekly_miner_refresh"
        )
        await scheduler.run_until_stopped()
```

### Integration with Existing System

**Database Connection** (reuse existing pattern):
```python
# From services/ai-automation-service/src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    "sqlite+aiosqlite:///data/ai_automation.db",
    echo=False
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session():
    async with async_session() as session:
        yield session
```

**Logging** (reuse existing pattern):
```python
# From shared/logging_config.py
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)

def log_operation(operation: str):
    correlation_id = str(uuid4())
    logger.info(f"[{correlation_id}] {operation} started")
    # ... operation ...
    logger.info(f"[{correlation_id}] {operation} completed")
```

**Health Check** (extend existing pattern):
```python
# From services/ai-automation-service/src/api/health.py
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "database": await check_db(),
            "automation_miner": await check_miner_corpus()  # NEW
        }
    }

async def check_miner_corpus() -> dict:
    """Check miner corpus health"""
    try:
        stats = await corpus_repo.get_stats()
        return {
            "status": "healthy",
            "corpus_count": stats['total'],
            "last_crawl": stats['last_crawl_time']
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Performance Considerations

**Query Optimization:**
- Index on `devices` (JSON array, use GIN index if PostgreSQL)
- Index on `integrations`, `use_case`, `quality_score`
- Cache query results for 5 minutes (use `@lru_cache` or Redis)

**Crawler Optimization:**
- Batch processing: 50 posts at a time
- Connection pooling: Reuse httpx client across requests
- Rate limiting: 2 requests/second to avoid API ban
- Async processing: Crawl + parse in parallel (asyncio.gather)

**Storage Optimization:**
- Store insights only (no raw YAML unless needed)
- JSON fields for dynamic data (devices, integrations)
- Prune low-quality entries (quality_score < 0.4) during refresh

### Error Scenarios

1. **Discourse API Down:**
   - Retry 3 times with exponential backoff (1s, 2s, 4s)
   - If all retries fail, log error and skip to next batch
   - Alert if >50% of requests fail

2. **Invalid YAML:**
   - Log warning with post ID
   - Skip automation (don't store invalid data)
   - Track parse failures for debugging

3. **Database Connection Lost:**
   - Graceful degradation: Return cached results if available
   - Retry database connection with backoff
   - Feature flag: Disable miner queries if DB unavailable

4. **Duplicate Detection:**
   - Use rapidfuzz for fuzzy title matching (>85% = duplicate)
   - Keep higher quality score
   - Log duplicate for manual review

### Testing Standards

**Unit Tests** (from `docs/architecture/coding-standards.md`):
- Location: `services/automation-miner/tests/unit/`
- Framework: pytest + pytest-asyncio
- Coverage: ≥80% for core logic (parser, normalizer)
- Mocking: Use `httpx-mock` for API tests

**Integration Tests:**
- Location: `services/automation-miner/tests/integration/`
- Test full flow: Crawl → Parse → Store → Query
- Use test database (in-memory SQLite)
- Test error scenarios (API timeout, invalid YAML)

**Performance Tests:**
- Load test query API: 100 concurrent requests
- Verify p95 latency <100ms
- Test initial crawl duration (<3 hours)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Story created with Context7 best practices | BMad Master |

---

## Dev Agent Record

### Agent Model Used
*Populated during implementation*

### Debug Log References
*Populated during implementation*

### Completion Notes List
*Populated during implementation*

### File List
*Populated during implementation*

---

## QA Results
*QA Agent review pending*

