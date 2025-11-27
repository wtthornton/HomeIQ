# Epic 39: AI Automation Service Modularization & Performance Optimization

**Epic ID:** 39  
**Title:** AI Automation Service Modularization & Performance Optimization  
**Status:** Planning  
**Priority:** High  
**Complexity:** High  
**Timeline:** 4-6 weeks  
**Story Points:** 40-60  
**Type:** Brownfield Enhancement  
**Related Analysis:** Service split analysis completed (see conversation history)

---

## Epic Goal

Refactor the monolithic AI Automation Service into a modular architecture that enables independent scaling, improved maintainability, and optimized performance while maintaining all existing functionality and performance requirements.

---

## Epic Description

### Existing System Context

**Deployment Context:**
- **Single-home NUC deployment** (Intel NUC i3/i5, 8-16GB RAM)
- Resource-constrained environment optimized for local processing
- All services run on one machine via Docker Compose
- AI Automation Service currently handles all AI-related functionality in one service

**Current Functionality:**
- **24+ API routers** with 121+ endpoints
- **93+ service files** across multiple domains
- **Large monolithic router** (`ask_ai_router.py` ~9,610 lines)
- Multiple concerns: query processing, pattern detection, training, deployment, learning
- Heavy dependencies: OpenAI, containerized models, MQTT, database, external services

**Technology Stack:**
- Python 3.12, FastAPI 0.115.x
- SQLite database (shared across services)
- MQTT for real-time capability listening
- Containerized AI models (OpenVINO, transformers)
- OpenAI API integration (GPT-5.1, GPT-5.1-mini)

**Current Architecture:**
```
ai-automation-service (Port 8018)
├── API Layer (24 routers)
│   ├── ask_ai_router.py (9,610 lines - CRITICAL BOTTLENECK)
│   ├── pattern_router.py
│   ├── suggestion_router.py
│   ├── training endpoints
│   └── ... 20+ more routers
├── Services Layer (93+ files)
│   ├── Entity extraction & validation
│   ├── Pattern detection & analysis
│   ├── Suggestion generation
│   ├── Training & ML models
│   ├── YAML generation & deployment
│   └── ... many more services
├── Database (SQLite)
├── MQTT Client
├── Model Services (containerized)
└── Scheduler (daily analysis)
```

**Performance Requirements:**
- Query latency: <500ms for Ask AI queries
- Database connections: Pooled, max 20 connections per service
- Token budgets: 7K entity context, 2K enrichment
- Model loading: Containerized models in separate containers
- Real-time MQTT: Capability listening

### Enhancement Details

**Hybrid Approach - Gradual Extraction Strategy:**

**Phase 1: Extract Training Service** (Lowest Risk)
- Move training functionality to separate service
- Reduces main service size and complexity
- Training can run on schedule/queue independently
- **Target:** `ai-training-service` (Port 8022)

**Phase 2: Extract Pattern Analysis Service** (Medium Risk)
- Move pattern detection & analysis to separate service
- Daily scheduler moves here
- Reduces main service CPU load
- **Target:** `ai-pattern-service` (Port 8020)

**Phase 3: Split Query vs Automation** (Higher Risk)
- Query service: User-facing, low latency requirements
- Automation service: YAML generation, deployment
- Shared database with proper connection pooling
- **Targets:** `ai-query-service` (Port 8018), `ai-automation-service` (Port 8021)

**Phase 4: Modular Monolith Refactor** (Internal Code Organization)
- Split large routers into focused modules
- Better service layer organization
- Extract background workers
- Maintains single deployment initially

**Success Criteria:**
- ✅ Training service extracted and operational
- ✅ Pattern analysis service extracted and operational
- ✅ Query and automation services split successfully
- ✅ All existing functionality maintained
- ✅ Performance requirements met (<500ms query latency)
- ✅ Database connection pooling optimized
- ✅ SQLite-based cache for entity/pattern data (existing CorrelationCache)
- ✅ Independent scaling capabilities enabled
- ✅ Zero breaking changes to external APIs

## Business Value

- **Independent Scaling**: Scale query service for user traffic, training service for batch jobs
- **Improved Maintainability**: Smaller, focused services are easier to understand and modify
- **Performance Optimization**: Specialized optimization per service (query: low latency, training: batch processing)
- **Reduced Complexity**: Break down 9,610-line router into manageable components
- **Resource Efficiency**: Better resource allocation (realtime: memory, batch: CPU)
- **Development Velocity**: Smaller codebases enable faster development cycles
- **Deployment Flexibility**: Deploy services independently without full system restart

## Success Criteria

- ✅ Training service extracted and operational
- ✅ Pattern analysis service extracted and operational
- ✅ Query and automation services split successfully
- ✅ All existing functionality maintained
- ✅ Performance requirements met (<500ms query latency)
- ✅ Database connection pooling optimized (max 20 connections per service)
- ✅ SQLite-based cache for entity/pattern data (existing CorrelationCache)
- ✅ Independent scaling capabilities enabled
- ✅ Zero breaking changes to external APIs
- ✅ All tests passing (unit, integration, E2E)
- ✅ Documentation updated
- ✅ Deployment guide updated

## Technical Architecture

### Target Architecture (Phase 3 Complete)

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer               │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ai-query-    │  │ ai-pattern-  │  │ ai-training- │
│ service      │  │ service       │  │ service      │
│ (Port 8018)  │  │ (Port 8020)  │  │ (Port 8022)  │
│              │  │              │  │              │
│ - Ask AI     │  │ - Pattern    │  │ - Synthetic  │
│ - Conversa-  │  │   Detection   │  │   Data Gen   │
│   tional     │  │ - Synergy     │  │ - Model      │
│ - Entity     │  │ - Analysis    │  │   Training   │
│   Extraction │  │ - Scheduler   │  │ - Evaluation │
│ - Low        │  │ - Background  │  │ - Batch      │
│   Latency    │  │   Processing  │  │   Processing │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ai-automation│  │ Shared       │  │ SQLite-based │
│ -service     │  │ SQLite DB    │  │ Cache        │
│ (Port 8021)  │  │ (Connection  │  │ (Correlation │
│              │  │ Pooling)     │  │ Cache)       │
│ - Suggestion │  │              │  │              │
│   Generation │  │              │  │              │
│ - YAML Gen   │  │              │  │              │
│ - Deployment │  │              │  │              │
│ - Testing    │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Shared Infrastructure

**Database:**
- SQLite with connection pooling (max 20 connections per service)
- Shared schema across services
- Migration strategy for gradual extraction

**Caching:**
- SQLite-based CorrelationCache (existing implementation)
- Two-tier: In-memory LRU + SQLite persistence
- Shared cache database across services (optional)
- TTL: 1 hour for correlations, configurable per cache type
- Memory footprint: <20MB for SQLite cache
- Optimized for single-home NUC deployment (no Redis needed)

**Message Queue (Optional):**
- RabbitMQ or MQTT for async communication
- Training job queue
- Pattern analysis queue

**Service Discovery:**
- Docker Compose service names
- Environment variables for service URLs
- Health check endpoints

### Resource Constraints (NUC Deployment)

**Memory Optimization:**
- Each service: <500MB memory footprint
- Shared database connections: Pooled
- Model containers: Separate, on-demand loading
- Target: Total <4GB for all AI services

**Performance Targets:**
- Query service: <500ms response time (P95)
- Pattern service: Background processing acceptable
- Training service: Batch processing, can queue
- Database queries: <50ms per query (P95)

**2025 Best Practices:**
- FastAPI async/await patterns
- Pydantic v2 for validation
- SQLAlchemy 2.0 async sessions
- Structured logging
- Type hints throughout
- Context7 KB patterns

## Stories

### Phase 1: Training Service Extraction

#### Story 39.1: Training Service Foundation
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Create new `ai-training-service` with FastAPI app, extract training router endpoints, set up Docker service, configure database connection pooling
- **Acceptance Criteria**:
  - ✅ New service created at `services/ai-training-service/`
  - ✅ Training endpoints extracted from main service
  - ✅ Docker service configured (Port 8022)
  - ✅ Database connection pooling configured
  - ✅ Health endpoint operational
  - ✅ All training tests passing

#### Story 39.2: Synthetic Data Generation Migration
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Move synthetic data generators to training service, update imports, verify integration
- **Acceptance Criteria**:
  - ✅ All synthetic generators moved to training service
  - ✅ Integration tests passing
  - ✅ Data generation pipeline operational
  - ✅ No breaking changes to existing scripts

#### Story 39.3: Model Training Migration
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Move model training code (home type, soft prompts, GNN) to training service, update model storage paths
- **Acceptance Criteria**:
  - ✅ All training scripts moved
  - ✅ Model storage configured
  - ✅ Training jobs operational
  - ✅ Model comparison service migrated

#### Story 39.4: Training Service Testing & Validation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Comprehensive testing of training service, integration tests, performance validation
- **Acceptance Criteria**:
  - ✅ Unit tests passing (>80% coverage)
  - ✅ Integration tests passing
  - ✅ Performance targets met
  - ✅ Documentation updated

### Phase 2: Pattern Analysis Service Extraction

#### Story 39.5: Pattern Service Foundation
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Create new `ai-pattern-service`, extract pattern detection & analysis code, configure scheduler migration
- **Acceptance Criteria**:
  - ✅ New service created (Port 8020)
  - ✅ Pattern detection code extracted
  - ✅ Synergy detection code extracted
  - ✅ Community patterns code extracted
  - ✅ Database connection pooling configured

#### Story 39.6: Daily Scheduler Migration
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Move daily analysis scheduler to pattern service, update MQTT client configuration, verify scheduled jobs
- **Acceptance Criteria**:
  - ✅ Scheduler moved to pattern service
  - ✅ MQTT client configured
  - ✅ Scheduled jobs operational
  - ✅ No duplicate scheduling

#### Story 39.7: Pattern Learning & RLHF Migration
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Move pattern learning, RLHF, and quality scoring to pattern service
- **Acceptance Criteria**:
  - ✅ Learning services migrated
  - ✅ RLHF pipeline operational
  - ✅ Quality scoring functional
  - ✅ Tests passing

#### Story 39.8: Pattern Service Testing & Validation
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Comprehensive testing of pattern service, integration tests, scheduler validation
- **Acceptance Criteria**:
  - ✅ Unit tests passing
  - ✅ Integration tests passing
  - ✅ Scheduler jobs verified
  - ✅ Performance targets met

### Phase 3: Query & Automation Service Split

#### Story 39.9: Query Service Foundation
- **Story Points**: 8
- **Priority**: P0
- **Effort**: 6-8 hours
- **Description**: Create `ai-query-service`, extract Ask AI router (split into smaller modules), extract conversational endpoints, optimize for low latency
- **Acceptance Criteria**:
  - ✅ Query service created (Port 8018)
  - ✅ Ask AI router split into manageable modules
  - ✅ Conversational endpoints extracted
  - ✅ Entity extraction optimized
  - ✅ Response time <500ms (P95)

#### Story 39.10: Automation Service Foundation
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Create `ai-automation-service` (new), extract suggestion generation, YAML generation, deployment, testing
- **Acceptance Criteria**:
  - ✅ Automation service created (Port 8021)
  - ✅ Suggestion generation extracted
  - ✅ YAML generation extracted
  - ✅ Deployment endpoints extracted
  - ✅ All endpoints operational

#### Story 39.11: Shared Infrastructure Setup
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-6 hours
- **Description**: Configure shared SQLite-based cache (CorrelationCache), configure shared database connection pooling, implement service-to-service communication
- **Acceptance Criteria**:
  - ✅ SQLite-based cache configured and shared across services
  - ✅ Database connection pooling optimized
  - ✅ Service communication working
  - ✅ Cache hit rate >80%

#### Story 39.12: Query & Automation Service Testing
- **Story Points**: 4
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Comprehensive testing of both services, integration tests, performance validation, latency testing
- **Acceptance Criteria**:
  - ✅ All tests passing
  - ✅ Performance targets met
  - ✅ Latency <500ms verified
  - ✅ Integration tests passing

### Phase 4: Code Organization & Optimization

#### Story 39.13: Router Modularization
- **Story Points**: 5
- **Priority**: P1
- **Effort**: 4-6 hours
- **Description**: Split large routers into focused modules, extract common logic, improve code organization
- **Acceptance Criteria**:
  - ✅ Large routers split into modules
  - ✅ Code organization improved
  - ✅ No functionality changes
  - ✅ Tests passing

#### Story 39.14: Service Layer Reorganization
- **Story Points**: 4
- **Priority**: P1
- **Effort**: 3-4 hours
- **Description**: Reorganize service layer by domain, improve dependency injection, extract background workers
- **Acceptance Criteria**:
  - ✅ Services organized by domain
  - ✅ Dependency injection improved
  - ✅ Background workers extracted
  - ✅ Code maintainability improved

#### Story 39.15: Performance Optimization
- **Story Points**: 5
- **Priority**: P1
- **Effort**: 4-6 hours
- **Description**: Optimize database queries, implement caching strategies, optimize token usage, profile and optimize hot paths
- **Acceptance Criteria**:
  - ✅ Database queries optimized
  - ✅ Caching strategies implemented
  - ✅ Token usage optimized
  - ✅ Performance targets exceeded

#### Story 39.16: Documentation & Deployment Guide
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Update architecture documentation, create deployment guide, update API documentation
- **Acceptance Criteria**:
  - ✅ Architecture docs updated
  - ✅ Deployment guide created
  - ✅ API docs updated
  - ✅ Service communication documented

## Dependencies

### External Dependencies
- SQLite-based cache (CorrelationCache) - Already implemented, no additional infrastructure needed
- Docker Compose (for service orchestration) - Already in use
- Shared database (SQLite) - Already in use

### Internal Dependencies
- Existing AI Automation Service codebase
- Database schema (shared across services)
- Model containers (already containerized)
- MQTT broker (already configured)

### Story Dependencies
- **Phase 1**: Stories 39.1-39.4 (sequential within phase)
- **Phase 2**: Stories 39.5-39.8 (sequential within phase, can start after Phase 1)
- **Phase 3**: Stories 39.9-39.12 (sequential within phase, depends on Phase 1-2)
- **Phase 4**: Stories 39.13-39.16 (can be done in parallel, depends on Phase 3)

## Risks & Mitigation

### High Risk
- **Breaking Changes During Migration**: Mitigation through comprehensive testing, gradual extraction, backward compatibility checks
- **Performance Degradation**: Mitigation through performance testing at each phase, connection pooling, caching strategies
- **Database Connection Issues**: Mitigation through proper connection pooling, max connection limits, monitoring

### Medium Risk
- **Service Communication Complexity**: Mitigation through well-defined APIs, service discovery, health checks
- **Data Consistency**: Mitigation through shared database with proper transaction handling, cache invalidation strategies
- **Deployment Complexity**: Mitigation through Docker Compose orchestration, gradual rollout, rollback plan

### Low Risk
- **Code Duplication**: Mitigation through shared libraries, common utilities, code review
- **Testing Coverage**: Mitigation through comprehensive test suite, integration tests, E2E tests

## Testing Strategy

### Unit Tests
- Each service has comprehensive unit tests
- Test coverage >80% for all services
- Mock external dependencies (OpenAI, MQTT, database)

### Integration Tests
- Service-to-service communication
- Database operations across services
- Cache operations
- MQTT message handling

### Performance Tests
- Query latency (<500ms P95)
- Database connection pooling
- Cache hit rates (>80%)
- Memory usage per service (<500MB)

### E2E Tests
- Full user workflows across services
- Training pipeline end-to-end
- Pattern analysis end-to-end
- Query to deployment workflow

## Acceptance Criteria

- [ ] Training service extracted and operational
- [ ] Pattern analysis service extracted and operational
- [ ] Query and automation services split successfully
- [ ] All existing functionality maintained
- [ ] Performance requirements met (<500ms query latency)
- [ ] Database connection pooling optimized (max 20 connections per service)
- [ ] SQLite-based cache for entity/pattern data (existing CorrelationCache)
- [ ] Independent scaling capabilities enabled
- [ ] Zero breaking changes to external APIs
- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation updated
- [ ] Deployment guide updated

## Definition of Done

- [ ] All Phase 1 stories completed (Training Service)
- [ ] All Phase 2 stories completed (Pattern Service)
- [ ] All Phase 3 stories completed (Query & Automation Split)
- [ ] All Phase 4 stories completed (Code Organization)
- [ ] All services operational and tested
- [ ] Performance targets met
- [ ] Database connection pooling optimized
- [ ] SQLite-based cache operational and shared across services
- [ ] All tests passing (>80% coverage)
- [ ] Documentation complete
- [ ] Deployment guide complete
- [ ] Code review completed
- [ ] QA approval received

## Epic Completion Summary

**Status:** Planning  
**Target Start:** TBD  
**Target Completion:** TBD

### Stories Planned (16 total)
- **Phase 1 (Training)**: 4 stories (18 story points)
- **Phase 2 (Pattern)**: 4 stories (17 story points)
- **Phase 3 (Query/Automation)**: 4 stories (22 story points)
- **Phase 4 (Optimization)**: 4 stories (17 story points)

### Estimated Timeline
- **Phase 1**: 1-1.5 weeks
- **Phase 2**: 1-1.5 weeks
- **Phase 3**: 1.5-2 weeks
- **Phase 4**: 1 week
- **Total**: 4.5-6 weeks

### Success Metrics
- Query latency: <500ms (P95)
- Database connections: <20 per service
- Cache hit rate: >80%
- Memory per service: <500MB
- Test coverage: >80%
- Zero breaking changes

---

**Created**: December 2025  
**Last Updated**: December 2025  
**Author**: BMAD Master  
**Reviewers**: System Architect, QA Lead  
**Related Analysis**: Service split analysis (conversation history)  
**Deployment Context**: Single-home NUC (Intel NUC i3/i5, 8-16GB RAM) - see `docs/prd.md` section 1.7  
**Context7 KB References**: 
- FastAPI patterns: `docs/kb/context7-cache/fastapi-pydantic-settings.md`
- Microservices patterns: `docs/kb/context7-cache/` (if available)
- Service architecture: `docs/architecture.md`

