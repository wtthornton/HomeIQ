---
epic: external-service-connector-standardization
priority: high
status: open
estimated_duration: 2-3 weeks
risk_level: medium
source: Architecture review of full domain stack (2026-03-01; counts: service-groups.md)
---

# Epic 13: External Service Connector Standardization

**Status:** Open
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium
**Source:** Duplicated boilerplate analysis across 50 HomeIQ microservices
**Affects:** Services using InfluxDB, Data API, HTTP clients, and OpenAI in `domains/`

## Context

Multiple services independently implement HTTP client lifecycle management for the same external services: InfluxDB (3 implementations, ~540 lines), Data API (7 implementations, ~350 lines each), OpenAI (3 implementations, ~300 lines), and generic HTTP sessions (7+ services, ~400 lines). Each implementation duplicates connection setup, retry logic, circuit breaker configuration, health probes, and teardown. The `DatabaseManager` standardization (completed Mar 1) proved this extraction pattern works for database connectors — the same approach applies to HTTP-based connectors.

## Stories

### Story 13.1: InfluxDBWriteService — Standardized InfluxDB Client

**Priority:** High | **Estimate:** 1.5 days | **Risk:** Medium

**Problem:** 3 services implement InfluxDB client setup independently with 150-590 lines each. All follow the same pattern: `InfluxDBClient()` -> `write_api()` -> `query_api()`, `asyncio.to_thread()` for sync writes, health checks via aiohttp. Retry/backoff logic exists in automation-trace-service but not in others. Connection configuration is scattered across env vars, settings objects, and hardcoded URLs.

**Files:**
- New: `libs/homeiq-data/src/homeiq_data/influxdb_manager.py`
- Modify: `libs/homeiq-data/src/homeiq_data/__init__.py` (add export)
- Migrate:
  - `domains/core-platform/websocket-ingestion/src/influxdb_wrapper.py` (590 lines)
  - `domains/automation-core/automation-trace-service/src/influxdb_writer.py` (143 lines)
  - `domains/core-platform/admin-api/src/influxdb_client.py` (404 lines)

**Acceptance Criteria:**
- [ ] `InfluxDBManager` class in `homeiq-data` with: connect, write, query, health check, close
- [ ] Thread-safe writes via `asyncio.to_thread()` built-in (no per-service wrapping)
- [ ] Retry with exponential backoff for write operations (standardized from trace-service pattern)
- [ ] Health check via `/health` and `/ping` endpoints (from websocket-ingestion pattern)
- [ ] URL resolution: explicit param > `INFLUXDB_URL` env var > default
- [ ] Connection pooling and lifecycle managed internally
- [ ] 3 services migrated with no write/query behavior changes
- [ ] Unit tests for connect, write, retry, and health check scenarios

---

### Story 13.2: BaseDataAPIClient — Standardized Data API Connector

**Priority:** High | **Estimate:** 1.5 days | **Risk:** Low

**Problem:** 7 services each implement a `DataAPIClient` class (~160-200 lines) with identical `CrossGroupClient` setup (core-platform group, 30s timeout, 3 retries), module-level circuit breaker (`_core_platform_breaker`), and response parsing (check for list vs dict, extract field, handle empty). Auth key resolution varies: settings object, env vars, or explicit parameter. Error handling differs: some return empty lists on circuit open, others raise.

**Files:**
- New: `libs/homeiq-data/src/homeiq_data/data_api_client.py`
- Modify: `libs/homeiq-data/src/homeiq_data/__init__.py` (add export)
- Migrate:
  - `domains/automation-core/ai-automation-service-new/src/clients/data_api_client.py` (202 lines)
  - `domains/pattern-analysis/ai-pattern-service/src/clients/data_api_client.py` (304 lines)
  - `domains/automation-core/ha-ai-agent-service/src/clients/data_api_client.py` (264 lines)
  - 4 additional services with lighter Data API usage

**Acceptance Criteria:**
- [ ] `BaseDataAPIClient` class in `homeiq-data` with: standard CrossGroupClient setup, shared circuit breaker, response parsing utilities
- [ ] Auth key resolution: explicit param > `DATA_API_KEY` env var > `API_KEY` env var > None
- [ ] Common methods: `fetch_events()`, `fetch_entities()`, `fetch_devices()` with standardized response parsing
- [ ] Circuit breaker behavior configurable: return empty (default) or raise on open
- [ ] Per-service subclasses add only service-specific query methods
- [ ] 7 services migrated — client files reduced from ~200 lines to ~20 lines (subclass + custom methods)
- [ ] Unit tests for auth resolution, response parsing, and circuit breaker fallback

---

### Story 13.3: HttpSessionManager — Shared HTTP Client Lifecycle

**Priority:** Medium | **Estimate:** 1 day | **Risk:** Low

**Problem:** 7+ services create `aiohttp.ClientSession` or `httpx.AsyncClient` instances per-request instead of sharing a long-lived session. Each service duplicates timeout configuration, header setup, and session teardown. Some services (websocket-ingestion, admin-api) create new sessions for every health check, wasting TCP connections.

**Files:**
- New: `libs/homeiq-resilience/src/homeiq_resilience/http_session.py`
- Modify: `libs/homeiq-resilience/src/homeiq_resilience/__init__.py` (add export)
- Migrate:
  - `domains/core-platform/websocket-ingestion/src/influxdb_wrapper.py` (per-request aiohttp sessions)
  - `domains/core-platform/admin-api/src/influxdb_client.py` (per-request aiohttp sessions)
  - `domains/ml-engine/openai-service/src/openai_service.py` (per-request httpx client)
  - 4+ additional services with ad-hoc HTTP client creation

**Acceptance Criteria:**
- [ ] `HttpSessionManager` class in `homeiq-resilience` with: shared session creation, default headers, timeout config, graceful close
- [ ] Support for both `aiohttp` and `httpx` backends (configurable)
- [ ] Session created on first use, closed in lifespan shutdown (not per-request)
- [ ] Default timeout, retry, and connection pool configuration
- [ ] 7+ services migrated — no per-request session creation
- [ ] Unit tests for session lifecycle, timeout handling, and concurrent access

---

### Story 13.4: OpenAIClientManager — Standardized OpenAI Integration

**Priority:** Medium | **Estimate:** 1.5 days | **Risk:** Medium

**Problem:** 3 services implement OpenAI client setup with 80-150 lines each. Two (ha-ai-agent-service, ai-automation-service-new) use `AsyncOpenAI` with identical tenacity retry decorators (`@retry(retry_if_exception_type(...), stop_after_attempt(3), wait_exponential(...))`). One (openai-service) uses raw httpx. Model selection logic, token tracking, temperature handling for reasoning models, and fine-tuned model support are implemented independently.

**Files:**
- New: `libs/homeiq-resilience/src/homeiq_resilience/openai_manager.py`
- Modify: `libs/homeiq-resilience/src/homeiq_resilience/__init__.py` (add export)
- Migrate:
  - `domains/automation-core/ha-ai-agent-service/src/services/openai_client.py` (100+ lines)
  - `domains/automation-core/ai-automation-service-new/src/clients/openai_client.py` (100+ lines)
  - `domains/ml-engine/openai-service/src/openai_service.py` (63 lines — raw httpx)

**Acceptance Criteria:**
- [ ] `OpenAIClientManager` class in `homeiq-resilience` with: client initialization, retry logic, model selection, token tracking
- [ ] Tenacity retry built-in: `RateLimitError` + `APIError`, 3 attempts, exponential backoff
- [ ] Model selection: explicit param > `OPENAI_FINE_TUNED_MODEL` env var > settings > default
- [ ] Temperature handling: auto-disabled for reasoning models (o1, o3, gpt-5 prefixes)
- [ ] Token usage tracking: total_tokens, reasoning_tokens, request count, error count
- [ ] API key validation: graceful degradation when key not configured (returns None, logs warning)
- [ ] 3 services migrated — OpenAI client code reduced from ~100 lines to ~10 lines
- [ ] Unit tests for retry behavior, model selection, temperature handling, and fallback
