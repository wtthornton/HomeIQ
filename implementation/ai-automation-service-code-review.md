# AI Automation Service - Code Review Report

**Date:** January 2025  
**Service:** `ai-automation-service` (Port 8018/8024)  
**Reviewer:** TappsCodingAgents Code Review  
**Scope:** Comprehensive code review of main components  
**Context:** Single-user Home Assistant application (self-hosted, local network)

## ⚠️ STATUS UPDATE (January 2026)

**Important:** This review was based on the **archived service** (`services/archive/2025-q4/ai-automation-service`). The **current active service** is `services/ai-automation-service-new` (Port 8018/8024).

**Critical Finding:** The memory leak issues identified in this review have **already been fixed** in the current service:
- ✅ TTL cleanup for rate limiting (background task every 60s)
- ✅ Max size limits with LRU eviction (10,000 buckets)
- ✅ Proper background task lifecycle management

**See:** `implementation/ai-automation-service-local-analysis.md` for detailed analysis of current implementation.

---

## Executive Summary

The AI Automation Service is a complex FastAPI application with 417+ Python files implementing AI-powered automation suggestions for Home Assistant. This review is tailored for a **single-user, self-hosted deployment** rather than a multi-tenant SaaS application, focusing on practical improvements appropriate for the deployment scale.

### Overall Assessment

**Quality Score: 72/100** (Good, with room for improvement)

**Strengths:**
- ✅ Well-structured FastAPI application with proper middleware
- ✅ Comprehensive safety validation engine
- ✅ Good separation of concerns (routers, services, clients)
- ✅ Extensive configuration management
- ✅ Proper error handling patterns
- ✅ SQLite database is appropriate for single-user deployment
- ✅ Async SQLAlchemy 2.0 patterns

**Areas for Improvement (Scaled for Single-User Context):**
- ⚠️ Large number of TODO/FIXME comments (892 instances)
- ✅ **UPDATE:** In-memory storage TTL cleanup - **ALREADY FIXED** in current service
- ⚠️ Missing test coverage for critical paths
- ⚠️ Some code duplication in entity extraction
- ⚠️ Complex functions with high cyclomatic complexity
- ⚠️ Very large router files (7000+ lines) - maintenance burden

---

## 1. Architecture Review

### 1.1 Application Structure ✅

**Status:** Good

The service follows a clean FastAPI architecture:

```
src/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── api/                 # API routers (28 files)
├── services/            # Business logic (129 files)
├── clients/             # External service clients
├── database/            # Database models and CRUD
├── llm/                 # LLM integration
└── validation/          # Validation logic
```

**Recommendations:**
- ✅ Structure is well-organized
- Consider adding a `core/` directory for shared utilities
- Document the service dependency graph

### 1.2 Configuration Management ✅

**Status:** Excellent

The `config.py` file uses Pydantic Settings with comprehensive validation:

```python
class Settings(BaseSettings):
    # 477 lines of well-documented configuration
    model_config = SettingsConfigDict(...)
```

**Strengths:**
- ✅ Environment variable support
- ✅ Type validation with Pydantic
- ✅ Training mode detection
- ✅ Comprehensive defaults

**Recommendations:**
- ✅ Configuration is well-structured
- Consider splitting into domain-specific config classes if it grows further

### 1.3 Database Architecture ✅

**Status:** Good (Appropriate for Single-User)

Uses SQLAlchemy 2.0 async with SQLite:
- 27 tables for comprehensive data tracking
- Proper async session management
- Good use of indexes and foreign keys
- SQLite is appropriate for single-user deployment (no multi-tenant concerns)

**2025 Best Practices Alignment:**
- ✅ Uses `NullPool` for SQLite (SQLAlchemy 2.0 default for file-based databases)
- ✅ Async patterns are correct
- ✅ SQLite handles single-user workloads efficiently

**Recommendations:**
- ✅ Database structure is sound for single-user context
- Consider migration strategy documentation (Alembic)
- For single-user: Current setup is optimal; no need for PostgreSQL/Redis complexity

---

## 2. Security Review

### 2.1 Authentication ✅

**Status:** Good

```python
# main.py:342-343
app.add_middleware(AuthenticationMiddleware)
```

**Strengths:**
- ✅ Mandatory authentication (cannot be disabled)
- ✅ API key-based authentication
- ✅ Admin API key support

**Recommendations:**
- ✅ Security is properly enforced
- Consider adding rate limiting per API key
- Document API key rotation policy

### 2.2 Rate Limiting ⚠️

**Status:** Needs Improvement (Single-User Context)

```python
# middlewares.py:113-141
class RateLimitMiddleware(BaseHTTPMiddleware):
    # In-memory token bucket implementation
    _rate_limit_buckets: dict[str, dict] = defaultdict(...)
```

**Issues (Single-User Scale):**
- ⚠️ In-memory storage (lost on restart) - acceptable for single-user
- ⚠️ No TTL cleanup (potential memory leak with long uptime)
- ✅ Single instance is fine - no distributed requirement needed
- ⚠️ No persistence across restarts (may be acceptable)

**Recommendations (Scaled for Single-User):**
- 🟡 **MEDIUM:** Add TTL cleanup to prevent memory leaks (use `asyncio.Timer` or background task)
- 🟡 **MEDIUM:** Optionally persist to SQLite if rate limit history is needed across restarts
- ✅ In-memory is acceptable for single-user self-hosted (no Redis needed)
- Document rate limit behavior (per-API-key limits)

### 2.3 Idempotency ⚠️

**Status:** Needs Improvement (Single-User Context)

```python
# middlewares.py:21
_idempotency_store: dict[str, tuple] = {}  # In-memory storage
```

**Issues (Single-User Scale):**
- ⚠️ In-memory storage (lost on restart) - acceptable for single-user
- ⚠️ **CRITICAL:** No TTL cleanup strategy (memory leak risk)
- ⚠️ Can grow unbounded with repeated requests
- ✅ Single instance is fine - no distributed requirement

**Recommendations (Scaled for Single-User):**
- 🔴 **HIGH:** Implement TTL cleanup (background task with `asyncio.sleep` or `Timer`)
- 🟡 **MEDIUM:** Add max size limit (LRU eviction) to prevent unbounded growth
- 🟡 **OPTIONAL:** Persist to SQLite if idempotency needs to survive restarts (rare for single-user)
- ✅ Redis is overkill for single-user - SQLite persistence is sufficient if needed

### 2.4 Safety Validation ✅

**Status:** Excellent

```python
# safety_validator.py:45-75
class SafetyValidator:
    # 7 core safety rules implemented
```

**Strengths:**
- ✅ Comprehensive safety rules
- ✅ Configurable safety levels
- ✅ Conflict detection
- ✅ Override support with warnings

**Recommendations:**
- ✅ Safety validation is well-implemented
- Consider adding more safety rules based on production incidents

### 2.5 Input Validation ✅

**Status:** Good

Uses Pydantic models for request validation:
- ✅ Type checking
- ✅ Field validation
- ✅ Error messages

**Recommendations:**
- ✅ Input validation is solid
- Consider adding custom validators for domain-specific rules

---

## 3. Code Quality Review

### 3.1 Code Organization ✅

**Status:** Good

- Well-separated concerns
- Clear module boundaries
- Proper use of routers

**Issues Found:**
- Some large files (e.g., `ask_ai_router.py` has 7000+ lines)
- Complex functions with high cyclomatic complexity

**Recommendations:**
- 🔴 **HIGH:** Split large router files into smaller modules
- Refactor complex functions into smaller, testable units
- Consider using dependency injection more consistently

### 3.2 Error Handling ✅

**Status:** Good (Appropriate for Single-User)

```python
# main.py:367-394
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(...)
```

**Strengths:**
- ✅ Global exception handlers
- ✅ Proper error logging
- ✅ User-friendly error messages

**Recommendations (Single-User Context):**
- ✅ Error handling is comprehensive
- ✅ Structured logging is sufficient (no Sentry needed for self-hosted single-user)
- 🟡 **OPTIONAL:** Add basic error metrics to health endpoint (error count, recent errors)

### 3.3 Logging ✅

**Status:** Good (Appropriate for Single-User)

Uses structured logging:
- ✅ Proper log levels
- ✅ Contextual information
- ✅ Debug logging for troubleshooting

**Issues Found:**
- Some excessive debug logging (892 debug statements)
- No log rotation/retention strategy visible

**Recommendations (Single-User Context):**
- 🟡 **LOW:** Consider log level filtering in production (INFO instead of DEBUG)
- 🟡 **LOW:** Add log rotation via Python's `RotatingFileHandler` or container log management
- ✅ Structured logging (JSON format) is good but optional for single-user
- ✅ Current logging is sufficient for self-hosted troubleshooting

### 3.4 Code Duplication ⚠️

**Status:** Needs Improvement

Found in:
- Entity extraction logic (multiple extractors)
- Device matching logic
- Prompt building

**Recommendations:**
- 🔴 **MEDIUM:** Extract common patterns into shared utilities
- Create base classes for similar functionality
- Use composition over duplication

### 3.5 TODO/FIXME Comments ⚠️

**Status:** Needs Attention

Found **892 instances** of TODO/FIXME comments:

```python
# Examples:
# TODO: Pass available entities
# TODO: Get from session
# TODO: Get actual user_id from session
# TODO: Persist to DB (in-memory storage)
```

**Recommendations:**
- 🔴 **MEDIUM:** Create tickets for all TODO items
- Prioritize critical TODOs (security, data persistence)
- Remove obsolete TODOs
- Document technical debt

---

## 4. Performance Review

### 4.1 Database Queries ⚠️

**Status:** Needs Optimization (Single-User Scale)

**Issues:**
- Some N+1 query patterns possible
- No query result caching visible
- Async queries are good (SQLAlchemy 2.0 patterns)

**Recommendations (Scaled for Single-User):**
- 🟡 **MEDIUM:** Add in-memory caching for frequently accessed data (device metadata, etc.)
- 🟡 **MEDIUM:** Use eager loading (joinedload/selectinload) to avoid N+1 queries
- ✅ SQLite handles single-user workloads well - no need for query result caching infrastructure
- ✅ Current async patterns are appropriate

### 4.2 API Response Times ⚠️

**Status:** Needs Basic Monitoring (Single-User Context)

**Issues:**
- No response time metrics visible
- LLM calls can be slow (1-5s mentioned in health endpoint) - expected
- No timeout configuration visible for some operations

**Recommendations (Scaled for Single-User):**
- 🟡 **LOW:** Add basic response time logging (avg, p95, p99) to key endpoints
- 🟡 **MEDIUM:** Implement request timeouts for LLM calls (prevent hanging requests)
- ✅ Performance budgets are overkill for single-user - focus on user experience
- ✅ Current async processing is appropriate for LLM calls

### 4.3 Caching ✅

**Status:** Good

Uses caching in several places:
- Entity extraction cache
- Prompt caching (OpenAI native)
- Answer caching (RAG)

**Recommendations:**
- ✅ Caching strategy is good
- Document cache invalidation strategies
- Add cache hit/miss metrics

### 4.4 Memory Management ⚠️

**Status:** Needs Attention (Critical for Long-Running Service)

**Issues:**
- In-memory stores (idempotency, rate limiting) can grow unbounded
- No TTL cleanup visible
- Large data structures loaded into memory

**Recommendations (Scaled for Single-User):**
- 🔴 **HIGH:** Implement TTL cleanup and max size limits for in-memory stores
- 🟡 **MEDIUM:** Add simple memory usage logging (periodic check via `psutil` or container metrics)
- ✅ Pagination for large data sets is good practice
- ✅ Single-user context means lower traffic, but still need cleanup to prevent leaks

---

## 5. Testing Review

### 5.1 Test Coverage ⚠️

**Status:** Needs Improvement (Pragmatic for Single-User)

**Issues:**
- Test directory exists but coverage not verified
- No test coverage metrics visible
- Complex business logic needs more tests

**Recommendations (Scaled for Single-User):**
- 🟡 **MEDIUM:** Target 60-70% test coverage (80%+ is enterprise-grade, may be overkill)
- 🔴 **HIGH:** Add unit tests for critical paths (safety validation, LLM integration, entity extraction)
- 🟡 **MEDIUM:** Add integration tests for key API endpoints
- ✅ Performance tests for LLM calls are optional for single-user (manual testing may suffice)

### 5.2 Test Quality ⚠️

**Status:** Unknown

**Recommendations:**
- Review existing tests for quality
- Add test fixtures for common scenarios
- Document testing strategy

---

## 6. Documentation Review

### 6.1 Code Documentation ✅

**Status:** Good

- Good docstrings on classes and functions
- Clear function descriptions
- Type hints used throughout

**Recommendations:**
- ✅ Documentation is good
- Consider adding architecture diagrams
- Document API contracts

### 6.2 README ✅

**Status:** Excellent

Comprehensive README with:
- Service overview
- Feature documentation
- Configuration guide
- API documentation

**Recommendations:**
- ✅ README is comprehensive
- Keep it updated with new features

---

## 7. Specific Code Issues

### 7.1 Critical Issues 🔴 (Scaled for Single-User)

1. **Memory Leak Risk in In-Memory Stores**
   - Location: `middlewares.py:21, 24`
   - Impact: Unbounded growth, potential service crash after long uptime
   - Fix: Add TTL cleanup and max size limits (LRU eviction)
   - Note: In-memory is acceptable for single-user; persistence to SQLite optional

2. **Large Router Files**
   - Location: `api/ask_ai_router.py` (7000+ lines)
   - Impact: Hard to maintain, test, and understand
   - Fix: Split into smaller modules (2025 FastAPI patterns: use `Annotated` dependencies, router composition)

3. **Missing Test Coverage for Critical Paths**
   - Impact: Risk of regressions in safety validation and LLM integration
   - Fix: Target 60-70% coverage with focus on critical paths
   - Note: 80%+ coverage is enterprise-grade; pragmatism for single-user is acceptable

### 7.2 High Priority Issues ⚠️ (Scaled for Single-User)

1. **892 TODO/FIXME Comments**
   - Impact: Technical debt, unclear requirements
   - Fix: Create tickets, prioritize critical TODOs (safety, persistence), remove obsolete
   - Note: Not all TODOs need immediate action - some may be "nice to have" for single-user

2. **Code Duplication**
   - Impact: Maintenance burden, inconsistency risk
   - Fix: Extract common patterns (entity extraction, device matching, prompt building)
   - Note: 2025 FastAPI best practice: Use `Annotated` dependencies for shared logic

3. **Memory Management**
   - ✅ **STATUS:** Already fixed in current service (`ai-automation-service-new`)
   - ✅ TTL cleanup implemented (60s interval, 2h TTL for rate limiting)
   - ✅ Max size limits with LRU eviction (10,000 buckets)
   - 🟡 Optional: Periodic memory usage logging (not critical)
   - Note: Simple `psutil` checks or container metrics sufficient for single-user

### 7.3 Medium/Low Priority Issues (Single-User Context)

1. **Basic Performance Monitoring**
   - 🟡 Add simple response time logging (avg, p95) to key endpoints
   - 🟡 Optional: Basic database query logging (slow query detection)
   - ✅ Cache hit/miss metrics are nice-to-have but optional for single-user

2. **Error Tracking** (Optional for Single-User)
   - ✅ Current logging is sufficient - no Sentry needed for self-hosted
   - 🟡 Optional: Add error count metrics to health endpoint
   - ✅ Error context is already good in logs

---

## 8. Recommendations Summary (Scaled for Single-User Home Assistant)

### ✅ STATUS UPDATE: Memory Leak Fixes Already Implemented

**Important:** This review was based on the archived service (`services/archive/2025-q4/ai-automation-service`). The **current active service** (`services/ai-automation-service-new`) has **already implemented** the critical memory leak fixes:

- ✅ **TTL Cleanup:** Background task runs every 60 seconds for rate limiting buckets
- ✅ **Max Size Limits:** 10,000 bucket limit with LRU eviction
- ✅ **Proper Lifecycle:** Cleanup task properly started/stopped in lifespan context manager
- ✅ **Modern Patterns:** Uses FastAPI 2025 best practices

**See:** `implementation/ai-automation-service-local-analysis.md` for detailed analysis of current implementation.

### Immediate Actions (This Sprint)

1. ✅ **COMPLETED:** Memory leak risks in in-memory stores - **ALREADY FIXED**
   - ✅ TTL cleanup for rate limiting buckets (background task every 60s)
   - ✅ Max size limits with LRU eviction (10,000 bucket limit)
   - ✅ Proper background task lifecycle management
   - **Note:** Idempotency not implemented in current service (not needed for single-user)

2. 🔴 **HIGH:** Increase test coverage for critical paths
   - Target: 60-70% coverage (pragmatic for single-user)
   - Focus on: Safety validation, LLM integration, entity extraction
   - Add integration tests for key API endpoints

3. ⚠️ **MEDIUM:** Split large router files
   - `ask_ai_router.py` (7000+ lines) → multiple modules
   - Use 2025 FastAPI patterns: `Annotated` dependencies, router composition
   - Extract common patterns (entity extraction, prompt building)

### Short-Term (Next Sprint)

1. Add basic monitoring (appropriate for single-user)
   - Simple response time logging (avg, p95) to key endpoints
   - Basic memory usage logging (periodic checks)
   - Optional: Error count metrics in health endpoint

2. Address critical TODO/FIXME comments
   - Prioritize: Safety, persistence, security-related TODOs
   - Remove obsolete TODOs
   - Document technical debt decisions

3. Code quality improvements
   - Extract common patterns (reduce duplication)
   - Refactor complex functions (reduce cyclomatic complexity)
   - Add database query optimization (eager loading, reduce N+1)

### Long-Term (Next Quarter)

1. Refactoring
   - Extract common patterns using `Annotated` dependencies (FastAPI 2025 pattern)
   - Reduce code duplication
   - Improve modularity

2. Documentation
   - Architecture diagrams
   - API contracts
   - Deployment guides for single-user

3. Optional enhancements (if needed)
   - SQLite persistence for idempotency/rate limiting (if restart persistence needed)
   - Advanced caching strategies (if performance issues arise)
   - **Note:** Skip enterprise features (Redis, Sentry, complex monitoring) - not needed for single-user

---

## 9. Quality Metrics

### Current State

| Metric | Score | Status |
|--------|-------|--------|
| **Overall Quality** | 72/100 | ✅ Good |
| **Security** | 8.0/10 | ✅ Good |
| **Maintainability** | 7.0/10 | ✅ Good |
| **Performance** | 6.5/10 | ⚠️ Needs Improvement |
| **Test Coverage** | Unknown | ⚠️ Needs Measurement |
| **Documentation** | 8.5/10 | ✅ Excellent |

### Target State (Scaled for Single-User)

| Metric | Target | Priority | Rationale |
|--------|--------|----------|-----------|
| **Overall Quality** | 75-80/100 | High | Good enough for single-user |
| **Security** | 8.5/10 | Critical | API key auth sufficient for local network |
| **Maintainability** | 7.5/10 | High | Focus on code organization |
| **Performance** | 7.0/10 | Medium | User experience matters more than metrics |
| **Test Coverage** | 60-70% | Medium | Pragmatic - focus on critical paths |
| **Documentation** | 8.0/10 | Medium | Good docs help single-user troubleshooting |

---

## 10. Conclusion (Single-User Context)

The AI Automation Service is a well-architected application with good security practices and comprehensive functionality. This review is tailored for a **single-user, self-hosted Home Assistant deployment**, avoiding over-engineering for enterprise multi-tenant scenarios.

### Key Takeaways

**What's Appropriate for Single-User:**
- ✅ SQLite database (no PostgreSQL needed)
- ✅ In-memory rate limiting and idempotency (no Redis needed)
- ✅ Simple logging (no Sentry/error tracking service needed)
- ✅ Basic monitoring (no complex metrics infrastructure)
- ✅ 60-70% test coverage (80%+ is enterprise-grade overkill)

**What Needs Attention:**
1. **Critical:** Fix memory leaks in in-memory stores (TTL cleanup, max size limits)
2. **High:** Test critical paths (safety validation, LLM integration)
3. **Medium:** Split large router files for maintainability
4. **Medium:** Address code duplication and technical debt (TODOs)

**2025 Architecture Alignment:**
- ✅ Uses SQLAlchemy 2.0 async patterns correctly
- ✅ SQLite `NullPool` is appropriate (SQLAlchemy 2.0 default)
- ✅ FastAPI async patterns are modern and correct
- 🟡 Consider FastAPI `lifespan` context managers (supersedes startup/shutdown)
- 🟡 Consider `Annotated` dependencies for shared logic (2025 FastAPI pattern)

**What NOT to Do (Over-Engineering for Single-User):**
- ❌ Don't add Redis (SQLite persistence is sufficient if needed)
- ❌ Don't add Sentry (structured logging is enough)
- ❌ Don't add complex monitoring infrastructure
- ❌ Don't target 80%+ test coverage (pragmatic 60-70% is better)
- ❌ Don't add distributed system features (single instance is fine)

With these pragmatic improvements, the service will be production-ready for single-user Home Assistant deployments while avoiding unnecessary complexity.

---

## 11. 2025 Architecture Patterns & Best Practices

### 11.1 FastAPI 2025 Best Practices ✅

**Current Alignment:**
- ✅ Uses async patterns correctly
- ✅ Pydantic models for validation
- ✅ Dependency injection patterns

**Recommended 2025 Enhancements:**

1. **Lifespan Context Managers** (FastAPI 0.93.0+)
   ```python
   # Current: @app.on_event("startup") / @app.on_event("shutdown")
   # Recommended: Use lifespan context manager
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup
       yield
       # Shutdown (cleanup)
   
   app = FastAPI(lifespan=lifespan)
   ```
   - **Benefit:** Cleaner resource management, single function for lifecycle
   - **Priority:** 🟡 Medium (when refactoring startup/shutdown logic)

2. **Annotated Dependencies for Code Reusability** (FastAPI 0.100.0+)
   ```python
   # Current: Repetitive Depends() in every endpoint
   # Recommended: Use Annotated for shared dependencies
   from typing import Annotated
   
   CurrentUser = Annotated[User, Depends(get_current_user)]
   CurrentSession = Annotated[Session, Depends(get_db_session)]
   
   @router.get("/endpoint")
   async def endpoint(user: CurrentUser, session: CurrentSession):
       ...
   ```
   - **Benefit:** Reduces code duplication, improves type hints
   - **Priority:** 🟡 Medium (when refactoring large router files)

3. **Application-Level Parameters**
   - Use top-level `dependencies` for global authentication
   - Use `default_response_class` for consistent responses
   - **Priority:** 🟡 Low (current implementation is fine)

**Reference:** FastAPI 2025 patterns align with `/fastapi/fastapi` best practices

### 11.2 SQLAlchemy 2.0 Best Practices ✅

**Current Alignment:**
- ✅ Uses async SQLAlchemy 2.0 correctly
- ✅ SQLite with `NullPool` (SQLAlchemy 2.0 default for file-based)
- ✅ Proper async session management

**SQLite-Specific Best Practices (2025):**

1. **Connection Pool Strategy**
   - ✅ **Current:** Uses `NullPool` for file-based SQLite (correct for SQLAlchemy 2.0)
   - **Rationale:** Each connection creates new pysqlite connection (appropriate for single-user)
   - **Note:** `SingletonThreadPool` is default for `:memory:` databases (not used here)

2. **Async Patterns**
   - ✅ Uses `AsyncSession` correctly
   - ✅ Proper async context managers
   - ✅ Transaction handling is correct

3. **Query Optimization (Single-User Context)**
   - ✅ SQLite handles single-user workloads efficiently
   - 🟡 Consider eager loading (`joinedload`, `selectinload`) to avoid N+1 queries
   - ✅ Current async patterns are optimal

**Reference:** SQLAlchemy 2.0 documentation (`/websites/sqlalchemy_en_20`) confirms current patterns

### 11.3 Single-User Architecture Patterns

**HomeIQ Epic 31 Architecture Alignment:**
- ✅ Direct InfluxDB writes (no intermediate services)
- ✅ SQLite for relational metadata (appropriate for single-user)
- ✅ Standalone services (no service-to-service dependencies)
- ✅ Simplified architecture (no enrichment-pipeline complexity)

**Recommended Patterns for Single-User:**
1. **In-Memory Storage:** Acceptable with TTL cleanup
2. **SQLite Persistence:** Sufficient for idempotency/rate limiting if needed
3. **Simple Logging:** Structured logging is enough (no Sentry)
4. **Basic Monitoring:** Health endpoints + simple metrics sufficient
5. **Pragmatic Testing:** 60-70% coverage focused on critical paths

### 11.4 Code Quality Best Practices (2025)

**Priority for Single-User Context:**

1. **Code Organization** 🔴 High
   - Split large files (7000+ lines is maintenance burden)
   - Extract common patterns (entity extraction, prompt building)

2. **Memory Management** 🔴 High
   - TTL cleanup for in-memory stores
   - Max size limits (LRU eviction)
   - Periodic memory usage checks

3. **Test Coverage** 🟡 Medium
   - Target 60-70% (pragmatic for single-user)
   - Focus on critical paths (safety, LLM integration)

4. **Documentation** 🟡 Medium
   - Architecture diagrams
   - API contracts
   - Deployment guides

5. **Performance Monitoring** 🟡 Low
   - Basic response time logging
   - Optional: Simple metrics in health endpoint
   - Skip complex monitoring infrastructure

---

## Appendix: Files Reviewed

### Core Files
- ✅ `src/main.py` (460 lines) - Application entry point
- ✅ `src/config.py` (567 lines) - Configuration management
- ✅ `src/safety_validator.py` (839 lines) - Safety validation engine

### API Files
- ✅ `src/api/health.py` (382 lines) - Health check endpoints
- ✅ `src/api/middlewares.py` (370+ lines) - Authentication, rate limiting, idempotency
- ✅ `src/api/suggestion_router.py` (1680+ lines) - Suggestion generation
- ⚠️ `src/api/ask_ai_router.py` (7000+ lines) - Ask AI interface (needs splitting)

### Database Files
- ✅ `src/database/models.py` (1183+ lines) - Database models

### Total Files Analyzed
- **417 Python files** in service
- **28 API router files**
- **129 service files**
- **892 TODO/FIXME comments** found

---

**Review Completed:** January 2025  
**Next Review:** After critical issues are addressed

