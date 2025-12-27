# Epic AI-21: Proactive Conversational Agent Service

**Status:** ✅ Complete  
**Type:** Brownfield Enhancement (New Service)  
**Priority:** High  
**Effort:** 10 Stories (28 story points, 4-5 weeks estimated)  
**Created:** January 2025  
**Last Updated:** December 2025  
**Completed:** December 2025  
**Dependencies:** Epic AI-20 (HA AI Agent Service - Completion) ✅

---

## Epic Goal

Create a new proactive conversational agent service that analyzes weather, sports, energy, and historical patterns to generate intelligent, context-aware prompts. This service calls the HA AI Agent Service (Epic AI-20) with enhanced prompts, enabling proactive automation suggestions that leverage external data sources and behavioral patterns. This complements the existing ai-automation-service pattern-based suggestions with context-aware conversational recommendations.

**Business Value:**
- **Proactive automation suggestions** - Agent suggests automations based on context (weather, sports, energy)
- **+50% suggestion relevance** - Context-aware prompts vs. generic suggestions
- **Enhanced user experience** - Natural language suggestions appear as conversations
- **Intelligent automation creation** - Leverages historical patterns + external data
- **Reduced user effort** - Agent proactively suggests instead of user asking

---

## Existing System Context

### Current Functionality

**Existing Services:**
- ✅ `ha-ai-agent-service` (Port 8030) - Conversational agent (Epic AI-20)
- ✅ `ai-automation-service` (Port 8018) - Pattern-based suggestions (3 AM batch)
- ✅ `weather-api` (Port 8009) - Weather data and forecasts
- ✅ `sports-data` (Port 8005) - Sports scores and schedules
- ✅ `carbon-intensity` (Port 8010) - Carbon intensity data
- ✅ `data-api` (Port 8006) - Historical event data and patterns

**Current Limitations:**
- ❌ No proactive conversational suggestions - Only reactive (user asks)
- ❌ No context-aware prompt generation - Generic suggestions only
- ❌ No agent-to-agent communication - Services don't communicate
- ❌ No weather/sports/energy integration for suggestions - Data exists but unused
- ❌ No scheduled proactive suggestions - Only 3 AM batch patterns

### Technology Stack (2025 Standards)

- **Service:** `services/proactive-agent-service/` (FastAPI 0.115.x, Python 3.12+)
- **Scheduler:** APScheduler 3.10+ (2025 async patterns)
- **HTTP Client:** httpx 0.27+ (async, for agent-to-agent calls)
- **Data Clients:** Reuse existing clients (weather-api, sports-data, data-api)
- **Database:** SQLite 3.x with SQLAlchemy 2.0+ (async)
- **API Framework:** FastAPI 0.115.x with Pydantic 2.9+
- **LLM Integration:** OpenAI Python SDK 1.54+ (for prompt generation)

### Integration Points

- **HA AI Agent Service:** HTTP API calls (agent-to-agent communication)
- **Weather API:** Forecast and current conditions
- **Sports Data:** Game schedules and scores
- **Carbon Intensity:** Grid carbon data
- **Data API:** Historical patterns and event data
- **Scheduler:** 3 AM daily batch job (or on-demand)

---

## Enhancement Details

### What's Being Added

1. **Proactive Agent Service** (NEW)
   - FastAPI service foundation (Port 8031)
   - Context analysis engine
   - Prompt generation service
   - Agent-to-agent communication client
   - Suggestion storage and management

2. **Context Analysis Engine** (NEW)
   - Weather analysis (forecasts, temperature trends)
   - Sports analysis (upcoming games, team schedules)
   - Energy analysis (carbon intensity, pricing)
   - Historical pattern analysis (usage patterns, co-occurrence)
   - Data aggregation and correlation

3. **Smart Prompt Generation** (NEW)
   - Context-aware prompt building
   - Natural language prompt formatting
   - Multi-context prompt assembly (weather + sports + patterns)
   - Prompt quality scoring
   - Template-based prompt generation

4. **Agent-to-Agent Communication** (NEW)
   - HTTP client for ha-ai-agent-service
   - Conversation initiation
   - Response handling
   - Error recovery
   - Retry logic

5. **Scheduler Integration** (NEW)
   - 3 AM daily batch job
   - On-demand trigger support
   - Job status tracking
   - Failure handling and retries

6. **Suggestion Management** (NEW)
   - Suggestion storage (SQLite)
   - Suggestion status tracking (pending, sent, approved, rejected)
   - User notification support (future)
   - Suggestion history

### How It Integrates

- **Non-Breaking:** New service, no impact on existing services
- **Complements ai-automation-service:** Different approach (context-aware vs. pattern-based)
- **Leverages ha-ai-agent-service:** Calls existing agent for automation creation
- **Reuses Data Sources:** Leverages existing weather, sports, energy services
- **Scheduled Execution:** Runs at 3 AM (same time as ai-automation-service batch)

### Success Criteria

1. **Functional:**
   - Service generates 3-5 proactive suggestions daily
   - Suggestions are contextually relevant (weather, sports, energy)
   - Agent-to-agent communication works reliably
   - Suggestions are stored and trackable

2. **Technical:**
   - Service response time <5 seconds per suggestion
   - 99.9% uptime for scheduled jobs
   - Agent-to-agent call success rate >95%
   - Unit tests >90% coverage

3. **Quality:**
   - Suggestions are relevant and actionable
   - Prompts are well-formed and natural
   - Error handling comprehensive
   - Logging and monitoring in place

---

## Stories

### Phase 1: Service Foundation & Context Analysis (Week 1-2)

#### Story AI21.1: Service Foundation & Architecture
**As a** developer,  
**I want** a new FastAPI service foundation,  
**so that** I can build the proactive agent service.

**Acceptance Criteria:**
1. New service directory `services/proactive-agent-service/`
2. FastAPI 0.115.x application setup
3. Port 8031 configuration
4. Health check endpoint (`GET /health`)
5. Docker configuration
6. Environment variable management (Pydantic Settings)
7. Logging configuration (structured logging)
8. Basic API documentation (OpenAPI)

**Effort:** 4-6 hours  
**Points:** 2

---

#### Story AI21.2: Context Analysis Engine
**As a** developer,  
**I want** a context analysis engine,  
**so that** I can analyze weather, sports, energy, and historical data.

**Acceptance Criteria:**
1. ContextAnalysisService class
2. Weather analysis (forecast, temperature trends, conditions)
3. Sports analysis (upcoming games, team schedules)
4. Energy analysis (carbon intensity, pricing trends)
5. Historical pattern analysis (usage patterns, co-occurrence)
6. Data aggregation and correlation logic
7. Error handling for missing data
8. Unit tests for analysis engine (>90% coverage)

**Effort:** 8-10 hours  
**Points:** 5

---

#### Story AI21.3: Data Client Integration
**As a** developer,  
**I want** clients for external data sources,  
**so that** I can fetch weather, sports, and energy data.

**Acceptance Criteria:**
1. WeatherAPIClient (connects to weather-api:8009)
2. SportsDataClient (connects to sports-data:8005)
3. CarbonIntensityClient (connects to carbon-intensity:8010)
4. DataAPIClient (connects to data-api:8006)
5. Async HTTP clients (httpx 0.27+)
6. Retry logic with exponential backoff
7. Error handling and graceful degradation
8. Unit tests for all clients

**Effort:** 6-8 hours  
**Points:** 3

---

### Phase 2: Prompt Generation & Agent Communication (Week 2-3)

#### Story AI21.4: Smart Prompt Generation
**As a** developer,  
**I want** a prompt generation service,  
**so that** I can create context-aware prompts for the HA AI Agent.

**Acceptance Criteria:**
1. PromptGenerationService class
2. Context-aware prompt building (weather + sports + energy + patterns)
3. Natural language prompt formatting
4. Multi-context prompt assembly
5. Prompt template system
6. Prompt quality scoring
7. Example prompt formats:
   - "It's going to be 95°F tomorrow. Should I create an automation to pre-cool your home?"
   - "Your team plays at 7 PM tonight. Should I create an automation to dim lights during the game?"
   - "Carbon intensity is low right now. Should I schedule your EV charging?"
8. Unit tests for prompt generation

**Effort:** 8-10 hours  
**Points:** 5

---

#### Story AI21.5: Agent-to-Agent Communication
**As a** developer,  
**I want** agent-to-agent communication,  
**so that** I can call the HA AI Agent Service with generated prompts.

**Acceptance Criteria:**
1. HAAgentClient class (HTTP client for ha-ai-agent-service:8030)
2. Conversation initiation (`POST /api/v1/chat`)
3. Response handling and parsing
4. Error recovery (retry logic)
5. Timeout handling (30 seconds default)
6. Response validation
7. Logging for agent-to-agent calls
8. Unit tests for communication client

**Effort:** 6-8 hours  
**Points:** 3

---

#### Story AI21.6: Suggestion Generation Pipeline
**As a** developer,  
**I want** a suggestion generation pipeline,  
**so that** I can generate proactive suggestions from context analysis.

**Acceptance Criteria:**
1. SuggestionGenerationPipeline class
2. Orchestrates: context analysis → prompt generation → agent call → storage
3. Batch processing (generate multiple suggestions)
4. Error handling at each stage
5. Suggestion quality filtering
6. Duplicate detection
7. Integration tests for full pipeline
8. Performance optimization (parallel processing)

**Effort:** 8-10 hours  
**Points:** 5

---

### Phase 3: Scheduler & Storage (Week 3-4)

#### Story AI21.7: Scheduler Integration
**As a** developer,  
**I want** scheduled batch jobs,  
**so that** proactive suggestions are generated automatically.

**Acceptance Criteria:**
1. APScheduler 3.10+ integration
2. 3 AM daily batch job
3. On-demand trigger support (`POST /api/v1/trigger`)
4. Job status tracking (started, running, completed, failed)
5. Job history storage
6. Failure handling and retries
7. Job cancellation support
8. Integration tests for scheduler

**Effort:** 6-8 hours  
**Points:** 3

---

#### Story AI21.8: Suggestion Storage & Management
**As a** developer,  
**I want** suggestion storage and management,  
**so that** suggestions are persisted and trackable.

**Acceptance Criteria:**
1. SQLite database schema (suggestions table)
2. SQLAlchemy 2.0 async models
3. Suggestion CRUD operations
4. Status tracking (pending, sent, approved, rejected)
5. Metadata storage (context used, prompt, response)
6. Indexes for performance (status, created_at)
7. Suggestion cleanup (TTL-based, 90 days default)
8. Database migrations (Alembic)
9. Unit tests for storage layer

**Effort:** 6-8 hours  
**Points:** 3

---

### Phase 4: API Endpoints & Testing (Week 4-5)

#### Story AI21.9: API Endpoints
**As a** developer,  
**I want** API endpoints for suggestion management,  
**so that** users can view and manage proactive suggestions.

**Acceptance Criteria:**
1. `GET /api/v1/suggestions` - List suggestions (paginated, filtered)
2. `GET /api/v1/suggestions/{id}` - Get suggestion details
3. `POST /api/v1/trigger` - Trigger on-demand suggestion generation
4. `GET /api/v1/jobs` - List scheduled jobs
5. `GET /api/v1/jobs/{id}` - Get job status
6. Request/response models (Pydantic 2.9+)
7. API documentation (OpenAPI/Swagger)
8. Integration tests for all endpoints

**Effort:** 6-8 hours  
**Points:** 3

---

#### Story AI21.10: Testing & Production Readiness
**As a** developer,  
**I want** comprehensive testing and production readiness,  
**so that** the service is reliable and maintainable.

**Acceptance Criteria:**
1. Unit tests for all services (>90% coverage)
2. Integration tests for full pipeline
3. End-to-end tests (context analysis → suggestion generation)
4. Mock external services (weather, sports, energy)
5. Performance tests (concurrent suggestion generation)
6. Error scenario testing
7. Documentation (API, deployment, configuration)
8. Monitoring setup (health checks, metrics)

**Effort:** 8-10 hours  
**Points:** 5

---

## Technical Assumptions (2025 Standards)

### Architecture Patterns
- **Microservice Architecture:** Standalone service following Epic 31 pattern
- **Agent-to-Agent Communication:** HTTP REST API calls (standard pattern)
- **Async/Await:** All I/O operations use async/await (Python 3.12+)
- **Event-Driven:** Scheduled jobs trigger suggestion generation
- **Separation of Concerns:** Analysis, generation, communication in separate services

### API Design
- **RESTful:** Standard REST patterns
- **OpenAPI 3.1:** Comprehensive API documentation
- **JSON:** Request/response format
- **Error Handling:** Consistent error response format

### Database
- **SQLite 3.x:** Embedded database for single-home deployment
- **Alembic:** Database migrations
- **Async Queries:** SQLAlchemy 2.0 async patterns

### Scheduling
- **APScheduler 3.10+:** Modern async scheduler
- **Cron-like:** 3 AM daily execution
- **Job Persistence:** Job state stored in database

### Security
- **API Key Management:** Environment variables
- **Rate Limiting:** Per-IP rate limiting (optional)
- **Input Validation:** Pydantic validation on all inputs

---

## Dependencies

- **Epic AI-20:** ✅ Required (HA AI Agent Service must be complete)
- **Weather API:** ✅ Existing (Port 8009)
- **Sports Data:** ✅ Existing (Port 8005)
- **Carbon Intensity:** ✅ Existing (Port 8010)
- **Data API:** ✅ Existing (Port 8006)

---

## Success Metrics

- **Suggestion Generation:** 3-5 suggestions per day
- **Relevance Score:** >70% of suggestions are relevant
- **Agent Communication:** >95% success rate for agent-to-agent calls
- **Response Time:** <5 seconds per suggestion generation
- **Uptime:** 99.9% availability for scheduled jobs

---

## Completion Status

**Epic AI-21 is COMPLETE** ✅

**All 10 Stories Implemented:**
- ✅ AI21.1: Service Foundation & Architecture
- ✅ AI21.2: Context Analysis Engine
- ✅ AI21.3: Data Client Integration
- ✅ AI21.4: Smart Prompt Generation
- ✅ AI21.5: Agent-to-Agent Communication
- ✅ AI21.6: Suggestion Generation Pipeline
- ✅ AI21.7: Scheduler Integration
- ✅ AI21.8: Suggestion Storage & Management
- ✅ AI21.9: API Endpoints
- ✅ AI21.10: Testing & Production Readiness

**Code Review:** ✅ Complete
- All issues identified and fixed
- Code compliant with Code Review Guide 2025
- Performance optimizations applied
- Exception handling improved

**Documentation:**
- ✅ Implementation Summary: `implementation/EPIC_AI21_IMPLEMENTATION_COMPLETE.md`
- ✅ Code Review Report: `implementation/EPIC_AI21_CODE_REVIEW_FIXES.md`
- ✅ Service README: `services/proactive-agent-service/README.md`

**Status:** Production Ready ✅

---

## Future Enhancements (Post-MVP)

- **User Preferences:** Learn user preferences for suggestion filtering
- **Notification System:** Push notifications for suggestions
- **Suggestion Feedback:** User feedback loop for improvement
- **Advanced Context:** More data sources (calendar, location, etc.)
- **Multi-home Support:** Support for multiple Home Assistant instances
- **Suggestion Analytics:** Usage metrics and insights

