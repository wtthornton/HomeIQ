# Proactive Agent Service Update Plan

**Date:** December 2025  
**Status:** 📋 Planning - Awaiting BMAD Approval  
**Epic:** TBD (To be created)  
**Based on:** HA AI Agent Service (Epic AI-19, AI-20)  
**Target:** Align proactive-agent-service with ha-ai-agent-service architecture and improvements  
**Standards:** 2025 Python 3.12+, FastAPI 0.115.x, Pydantic 2.x, SQLAlchemy 2.0 async

---

## BMAD Approval Status

### Review Status
- [ ] **Architect Review** - Pending
- [ ] **QA Review** - Pending  
- [ ] **PO Review** - Pending
- [ ] **Dev Review** - ✅ Complete (2025 Standards Verified)

### Approval Checklist
- [x] 2025 Technology Standards Verified (Python 3.12+, FastAPI 0.115.x, Pydantic 2.x)
- [x] Code Quality Standards Documented (Complexity A/B, Maintainability ≥65)
- [x] Testing Strategy Defined (>90% coverage target)
- [x] Backward Compatibility Ensured
- [x] Migration Strategy Defined
- [ ] Architecture Alignment Verified
- [ ] Risk Assessment Complete
- [ ] Story Breakdown Ready

---

## Executive Summary

This plan outlines the updates needed to align `proactive-agent-service` with the enhanced architecture and features implemented in `ha-ai-agent-service`. The primary goal is to ensure consistent patterns, improved context handling, and better integration between the two services.

**Key Changes Identified:**
1. Enhanced context injection system (Entity Attributes Service)
2. Improved conversation management and persistence
3. Better prompt assembly with token budget enforcement
4. Enhanced error handling and logging
5. Comprehensive health checks
6. Improved configuration management
7. Better agent-to-agent communication patterns

---

## 1. Context Analysis & Current State

### 1.1 HA AI Agent Service Changes (Reference)

#### Context Builder Enhancements
- **Entity Attributes Service** (NEW): Extracts effect lists, presets, themes from entity states
- **Enhanced Entity Inventory**: Friendly names, device IDs, aliases, states, icons
- **Enhanced Areas Service**: Friendly names, aliases, icons, labels
- **Enhanced Services Summary**: Full parameter schemas, enum values, constraints
- **Context Caching**: TTL-based caching (5-15 min per component)
- **Context Builder Initialization**: Proper async initialization and cleanup

#### Conversation Management
- **Conversation Persistence**: SQLite-backed with message history
- **Context Caching per Conversation**: 5 min TTL per conversation
- **Generic Message Filtering**: Filters out generic welcome messages
- **Token Budget Enforcement**: 16k token limit with intelligent truncation
- **Message History Management**: Truncates oldest messages when needed

#### Prompt Assembly
- **User Request Emphasis**: Wraps user messages with "USER REQUEST (process this immediately)"
- **Token Counting**: Accurate token counting with tiktoken
- **Token Budget**: Enforces 16k input token limit
- **System Prompt Integration**: Combines base prompt with Tier 1 context

#### Chat API
- **Tool Calling Support**: Full OpenAI function calling with multi-iteration loops
- **Rate Limiting**: 100 requests/minute per IP
- **Conversation Management**: Create, get, list, delete conversations
- **Error Handling**: Comprehensive error handling with graceful degradation

#### Configuration
- **Enhanced Settings**: More configuration options (timeouts, retries, TTLs)
- **Environment Variables**: Comprehensive environment variable support
- **Model Configuration**: GPT-5.1 support with optimized settings

#### Health Checks
- **Comprehensive Health Service**: Checks all dependencies
- **Health Status**: healthy/degraded/unhealthy status
- **Dependency Checks**: Database, HA, Data API, Device Intelligence, OpenAI

### 1.2 Proactive Agent Service Current State

#### Current Architecture
- **Context Analysis Service**: Analyzes weather, sports, energy, historical patterns
- **Prompt Generation Service**: Generates context-aware prompts
- **Suggestion Pipeline Service**: Orchestrates full pipeline
- **HA Agent Client**: HTTP client for agent-to-agent communication
- **Suggestion Storage**: SQLite-backed suggestion storage
- **Scheduler Service**: Daily batch job at 3 AM

#### Current Limitations
- **No Context Injection**: Doesn't leverage HA AI Agent's context system
- **Simple Prompt Generation**: Basic prompt templates without context awareness
- **Limited Error Handling**: Basic error handling without graceful degradation
- **No Health Checks**: Basic health endpoint only
- **Simple Configuration**: Limited configuration options
- **No Token Management**: No token counting or budget enforcement
- **No Conversation Management**: Creates new conversation for each suggestion

---

## 2. Update Requirements

### 2.1 High Priority Updates

#### 2.1.1 Enhanced HA Agent Client
**Current:** Basic HTTP client with retry logic  
**Target:** Enhanced client matching ha-ai-agent-service patterns

**Changes Needed:**
- Add conversation management support (create, reuse conversations)
- Add context refresh parameter support
- Enhanced error handling with graceful degradation
- Better response validation
- Support for tool call tracking
- Token tracking support

**Files to Update:**
- `services/proactive-agent-service/src/clients/ha_agent_client.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
from typing import Any
import logging
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class HAAgentClient:
    """Client for communicating with HA AI Agent Service (2025 patterns)"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False  # Graceful degradation
    )
    async def send_message(
        self,
        message: str,
        conversation_id: str | None = None,
        refresh_context: bool = False,
    ) -> dict[str, Any] | None:
        """Send message with conversation management (2025 async patterns).
        
        Args:
            message: Message/prompt to send
            conversation_id: Optional conversation ID (reuses if provided)
            refresh_context: Force context refresh (default: False)
            
        Returns:
            Response dict or None if unavailable (graceful degradation)
        """
        # Support conversation reuse
        # Support context refresh
        # Enhanced error handling with retry
```

#### 2.1.2 Context-Aware Prompt Generation
**Current:** Basic prompt templates  
**Target:** Context-aware prompts that leverage HA AI Agent's context system

**Changes Needed:**
- Understand HA AI Agent's context structure
- Generate prompts that work with injected context
- Reference specific entities, areas, services from context
- Use entity attributes (effect lists, presets) when relevant

**Files to Update:**
- `services/proactive-agent-service/src/services/prompt_generation_service.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
from typing import Any
import logging

logger = logging.getLogger(__name__)

class PromptGenerationService:
    """Service for generating context-aware prompts (2025 patterns)"""
    
    def _generate_weather_prompts(
        self, 
        weather_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate weather-based prompts with context awareness.
        
        Args:
            weather_data: Weather context from analysis service
            
        Returns:
            List of prompt dictionaries with context references
        """
        # Reference specific areas/devices from context
        # Use entity-friendly names instead of entity IDs
        # Include entity attributes when relevant
        # Follow 2025 Home Assistant patterns
```

#### 2.1.3 Conversation Management
**Current:** New conversation per suggestion  
**Target:** Reuse conversations for better context continuity

**Changes Needed:**
- Track conversation IDs per suggestion
- Reuse conversations when appropriate
- Support conversation management API
- Handle conversation cleanup

**Files to Update:**
- `services/proactive-agent-service/src/services/suggestion_pipeline_service.py`
- `services/proactive-agent-service/src/clients/ha_agent_client.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
from typing import Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class SuggestionPipelineService:
    """Orchestrates suggestion generation pipeline (2025 async patterns)"""
    
    def __init__(
        self,
        context_service: ContextAnalysisService | None = None,
        agent_client: HAAgentClient | None = None,
        storage_service: SuggestionStorageService | None = None,
    ) -> None:
        """Initialize pipeline service with dependency injection."""
        self.context_service = context_service or ContextAnalysisService()
        self.agent_client = agent_client or HAAgentClient()
        self.storage_service = storage_service or SuggestionStorageService()
        self.conversation_id: str | None = None  # Reuse conversation
    
    async def generate_suggestions(self) -> dict[str, Any]:
        """Generate suggestions with conversation management.
        
        Returns:
            Pipeline results dictionary
        """
        # Reuse conversation if available
        # Create new conversation if needed
        # Track conversation ID per suggestion
        # Follow 2025 async patterns
```

#### 2.1.4 Enhanced Error Handling
**Current:** Basic error handling  
**Target:** Comprehensive error handling with graceful degradation

**Changes Needed:**
- Graceful degradation when HA AI Agent unavailable
- Better error messages and logging
- Retry logic improvements
- Error categorization (transient vs permanent)

**Files to Update:**
- `services/proactive-agent-service/src/clients/ha_agent_client.py`
- `services/proactive-agent-service/src/services/suggestion_pipeline_service.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Enhanced error handling with exception chaining (B904 compliance)
try:
    agent_response = await self.agent_client.send_message(prompt)
except httpx.ConnectError as e:
    # Store suggestion as pending, retry later
    logger.warning(
        "HA AI Agent unavailable, suggestion stored for retry",
        exc_info=True
    )
    # Graceful degradation - store for retry
    await self.storage_service.mark_for_retry(suggestion_id)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        # Rate limit - back off and retry
        backoff_delay = 2 ** retry_count  # Exponential backoff
        await asyncio.sleep(backoff_delay)
    else:
        logger.error(f"HA AI Agent error: {e}", exc_info=True)
        raise  # Re-raise with exception chaining (B904)
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise  # Preserve exception chain (B904 compliance)
```

#### 2.1.5 Health Check Service
**Current:** Basic health endpoint  
**Target:** Comprehensive health checks matching ha-ai-agent-service

**Changes Needed:**
- Health check service with dependency checks
- Check HA AI Agent Service availability
- Check external service availability (weather, sports, energy)
- Check database connectivity
- Return health status (healthy/degraded/unhealthy)

**Files to Create:**
- `services/proactive-agent-service/src/services/health_check_service.py`

**Files to Update:**
- `services/proactive-agent-service/src/api/health.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
from typing import Any
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class HealthCheckService:
    """Comprehensive health check service (2025 async patterns)"""
    
    def __init__(
        self,
        settings: Settings,
        ha_agent_client: HAAgentClient,
        db_session: AsyncSession,
    ) -> None:
        """Initialize health check service."""
        self.settings = settings
        self.ha_agent_client = ha_agent_client
        self.db_session = db_session
    
    async def comprehensive_health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check (2025 async patterns).
        
        Returns:
            Health status dictionary with dependency checks
        """
        # Check HA AI Agent Service (async)
        # Check external services (weather, sports, energy)
        # Check database connectivity (SQLAlchemy 2.0 async)
        # Return health status (healthy/degraded/unhealthy)
        # Follow 2025 error handling patterns
```

### 2.2 Medium Priority Updates

#### 2.2.1 Configuration Enhancements
**Current:** Basic configuration  
**Target:** Enhanced configuration matching ha-ai-agent-service patterns

**Changes Needed:**
- Add timeout configurations
- Add retry configurations
- Add TTL configurations
- Add conversation management settings
- Better environment variable documentation

**Files to Update:**
- `services/proactive-agent-service/src/config.py`

**Implementation (2025 Standards - Pydantic 2.x):**
```python
from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings (Pydantic 2.x, 2025 patterns)"""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # HA AI Agent Service Configuration
    ha_ai_agent_url: str = Field(
        default="http://ha-ai-agent-service:8030",
        description="HA AI Agent Service URL"
    )
    ha_ai_agent_timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    ha_ai_agent_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts"
    )
    ha_ai_agent_conversation_ttl_days: int = Field(
        default=30,
        description="Conversation TTL in days"
    )
    
    # Suggestion Configuration
    suggestion_quality_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for suggestions"
    )
    max_suggestions_per_batch: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum suggestions per batch"
    )
    suggestion_retry_attempts: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed suggestions"
    )
```

#### 2.2.2 Token Management
**Current:** No token management  
**Target:** Basic token counting and budget awareness

**Changes Needed:**
- Add token counting utility
- Track token usage per suggestion
- Warn when prompts are too long
- Support token budget limits

**Files to Create:**
- `services/proactive-agent-service/src/utils/token_counter.py` (copy from ha-ai-agent-service)

**Files to Update:**
- `services/proactive-agent-service/src/services/prompt_generation_service.py`

**Implementation (2025 Standards):**
```python
from __future__ import annotations
from typing import Any
from ..utils.token_counter import count_tokens

def _score_prompt(self, prompt_data: dict[str, Any]) -> dict[str, Any]:
    """Score prompt quality with token awareness (2025 patterns).
    
    Args:
        prompt_data: Prompt dictionary with prompt text
        
    Returns:
        Prompt dictionary with added quality_score and token_count
    """
    # Count tokens using tiktoken (2025 standard)
    token_count = count_tokens(
        prompt_data["prompt"], 
        model="gpt-4o-mini"  # 2025 model reference
    )
    prompt_data["token_count"] = token_count
    
    # Penalize very long prompts (token budget awareness)
    score = prompt_data.get("quality_score", 0.5)
    if token_count > 500:
        score -= 0.1
    if token_count > 1000:
        score -= 0.2  # Significant penalty for very long prompts
    
    prompt_data["quality_score"] = max(0.0, min(1.0, score))
    return prompt_data
```

#### 2.2.3 Enhanced Logging
**Current:** Basic logging  
**Target:** Structured logging matching ha-ai-agent-service patterns

**Changes Needed:**
- Use shared logging configuration
- Add correlation IDs
- Enhanced log messages with context
- Better error logging

**Files to Update:**
- `services/proactive-agent-service/src/main.py`
- All service files

**Implementation (2025 Standards - Structured Logging):**
```python
from __future__ import annotations
import logging
import sys
from pathlib import Path

# Use shared logging with correlation IDs (2025 standard)
try:
    from shared.logging_config import setup_logging
except ImportError:
    # Fallback if shared logging not available
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    setup_logging = lambda name: logging.getLogger(name)

# Initialize structured logger with correlation ID support
logger = setup_logging("proactive-agent-service")
```

#### 2.2.4 Suggestion Metadata Enhancement
**Current:** Basic suggestion storage  
**Target:** Enhanced metadata tracking

**Changes Needed:**
- Track conversation IDs
- Track token usage
- Track tool calls
- Track response metadata
- Track retry attempts

**Files to Update:**
- `services/proactive-agent-service/src/services/suggestion_storage_service.py`
- `services/proactive-agent-service/src/models.py`

**Implementation (2025 Standards - SQLAlchemy 2.0):**
```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlalchemy import String, Integer, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Suggestion(Base):
    """Suggestion model (SQLAlchemy 2.0, 2025 patterns)"""
    
    __tablename__ = "suggestions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt: Mapped[str] = mapped_column(String(2000))
    context_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    
    # New fields (2025 enhancements)
    conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2.3 Low Priority Updates

#### 2.3.1 API Documentation
**Current:** Basic README  
**Target:** Comprehensive API documentation

**Changes Needed:**
- API endpoint documentation
- Request/response examples
- Error code documentation
- Integration examples

**Files to Create:**
- `services/proactive-agent-service/docs/API_DOCUMENTATION.md`
- `services/proactive-agent-service/docs/ENVIRONMENT_VARIABLES.md`

#### 2.3.2 Testing Enhancements
**Current:** Basic tests  
**Target:** Comprehensive test coverage

**Changes Needed:**
- Integration tests for HA Agent Client
- Tests for conversation management
- Tests for error handling
- Performance tests

**Files to Create/Update:**
- `services/proactive-agent-service/tests/test_ha_agent_client_integration.py`
- `services/proactive-agent-service/tests/test_conversation_management.py`
- `services/proactive-agent-service/tests/test_error_handling.py`

#### 2.3.3 Monitoring & Observability
**Current:** Basic logging  
**Target:** Enhanced monitoring

**Changes Needed:**
- Metrics collection
- Performance tracking
- Suggestion generation metrics
- Error rate tracking

**Files to Create:**
- `services/proactive-agent-service/src/services/metrics_service.py`

---

## 3. Implementation Plan

### Phase 1: Core Updates (Week 1)

#### Story 1: Enhanced HA Agent Client
**Effort:** 4-6 hours  
**Priority:** High

**Tasks:**
1. Update `ha_agent_client.py` with conversation management support
2. Add context refresh parameter
3. Enhance error handling with graceful degradation
4. Add response validation improvements
5. Update tests

**Acceptance Criteria:**
- Client supports conversation_id parameter
- Client supports refresh_context parameter
- Graceful degradation when HA AI Agent unavailable
- Enhanced error handling with retry logic
- All existing tests pass
- New tests for conversation management

#### Story 2: Conversation Management in Pipeline
**Effort:** 3-4 hours  
**Priority:** High

**Tasks:**
1. Add conversation tracking to SuggestionPipelineService
2. Implement conversation reuse logic
3. Update suggestion storage to track conversation IDs
4. Add conversation cleanup logic

**Acceptance Criteria:**
- Pipeline reuses conversations when appropriate
- Conversation IDs tracked per suggestion
- New conversations created when needed
- Conversation cleanup works correctly
- All tests pass

#### Story 3: Enhanced Error Handling
**Effort:** 3-4 hours  
**Priority:** High

**Tasks:**
1. Enhance error handling in HA Agent Client
2. Add error categorization (transient vs permanent)
3. Implement retry logic with backoff
4. Update pipeline to handle errors gracefully

**Acceptance Criteria:**
- Graceful degradation when services unavailable
- Retry logic with exponential backoff
- Error categorization works correctly
- Suggestions stored for retry when appropriate
- All tests pass

### Phase 2: Context & Prompt Enhancements (Week 2)

#### Story 4: Context-Aware Prompt Generation
**Effort:** 6-8 hours  
**Priority:** Medium

**Tasks:**
1. Update prompt generation to reference context
2. Use entity-friendly names instead of entity IDs
3. Include entity attributes when relevant
4. Enhance prompt templates with context awareness

**Acceptance Criteria:**
- Prompts reference specific entities/areas from context
- Entity-friendly names used in prompts
- Entity attributes included when relevant
- Prompt quality improved
- All tests pass

#### Story 5: Health Check Service
**Effort:** 4-6 hours  
**Priority:** Medium

**Tasks:**
1. Create HealthCheckService
2. Implement dependency checks
3. Update health endpoint
4. Add health status reporting

**Acceptance Criteria:**
- Health check service checks all dependencies
- Health status returned (healthy/degraded/unhealthy)
- Health endpoint returns comprehensive status
- All tests pass

### Phase 3: Configuration & Infrastructure (Week 3)

#### Story 6: Configuration Enhancements
**Effort:** 2-3 hours  
**Priority:** Medium

**Tasks:**
1. Update Settings class with new configuration options
2. Add timeout and retry configurations
3. Add conversation management settings
4. Update environment variable documentation

**Acceptance Criteria:**
- All new configuration options available
- Environment variables documented
- Configuration validation works
- All tests pass

#### Story 7: Token Management
**Effort:** 3-4 hours  
**Priority:** Medium

**Tasks:**
1. Copy token counter utility from ha-ai-agent-service
2. Add token counting to prompt generation
3. Track token usage per suggestion
4. Add token budget warnings

**Acceptance Criteria:**
- Token counting works correctly
- Token usage tracked per suggestion
- Warnings when prompts too long
- All tests pass

#### Story 8: Enhanced Logging
**Effort:** 2-3 hours  
**Priority:** Medium

**Tasks:**
1. Update to use shared logging configuration
2. Add correlation IDs
3. Enhance log messages with context
4. Improve error logging

**Acceptance Criteria:**
- Shared logging configuration used
- Correlation IDs in logs
- Enhanced log messages
- Better error logging
- All tests pass

### Phase 4: Metadata & Documentation (Week 4)

#### Story 9: Suggestion Metadata Enhancement
**Effort:** 3-4 hours  
**Priority:** Low

**Tasks:**
1. Update Suggestion model with new fields
2. Update storage service to track metadata
3. Update API to return metadata
4. Add migration for existing suggestions

**Acceptance Criteria:**
- New metadata fields added
- Metadata tracked correctly
- API returns metadata
- Migration works for existing data
- All tests pass

#### Story 10: Documentation
**Effort:** 4-6 hours  
**Priority:** Low

**Tasks:**
1. Create API documentation
2. Create environment variables documentation
3. Update README with new features
4. Add integration examples

**Acceptance Criteria:**
- API documentation complete
- Environment variables documented
- README updated
- Integration examples provided

---

## 4. Testing Strategy

### 4.1 Unit Tests (2025 Standards)
- **Framework:** pytest 8.0+ with pytest-asyncio
- **Coverage Target:** >90%
- **Test Files:** `test_*.py` pattern
- **Async Patterns:** All async tests use `@pytest.mark.asyncio`
- **Fixtures:** Use pytest fixtures for common setup
- **Test Scope:**
  - Test enhanced HA Agent Client (async patterns)
  - Test conversation management (SQLAlchemy 2.0 async)
  - Test error handling (exception chaining)
  - Test prompt generation improvements (token counting)
  - Test health check service (dependency checks)

### 4.2 Integration Tests (2025 Standards)
- **Framework:** pytest 8.0+ with pytest-asyncio
- **Test Scope:**
  - Test full pipeline with HA AI Agent Service (real HTTP calls)
  - Test conversation reuse (database persistence)
  - Test error handling scenarios (graceful degradation)
  - Test health check with real services (dependency verification)
- **Test Isolation:** Use test containers or mocks for external services
- **Async Patterns:** All integration tests use async/await

### 4.3 End-to-End Tests (2025 Standards)
- **Framework:** pytest 8.0+ with pytest-asyncio
- **Test Scope:**
  - Test suggestion generation flow (full pipeline)
  - Test conversation continuity (multi-turn interactions)
  - Test error recovery (retry logic, graceful degradation)
  - Test scheduled batch job (scheduler integration)
- **Test Data:** Use fixtures for consistent test data
- **Cleanup:** Ensure proper cleanup after tests

---

## 5. Migration Strategy

### 5.1 Database Migration
- Add new fields to Suggestion model
- Migrate existing suggestions (set defaults)
- No data loss expected

### 5.2 Configuration Migration
- New environment variables optional (have defaults)
- Existing configuration remains valid
- No breaking changes

### 5.3 API Compatibility
- All existing API endpoints remain compatible
- New optional fields added to responses
- No breaking changes

---

## 6. Success Criteria

### 6.1 Functional
- ✅ Enhanced HA Agent Client with conversation management
- ✅ Context-aware prompt generation
- ✅ Comprehensive error handling
- ✅ Health check service
- ✅ Configuration enhancements
- ✅ Token management
- ✅ Enhanced logging

### 6.2 Technical (2025 Standards)
- ✅ All tests pass (>90% coverage target)
- ✅ No breaking changes (backward compatible)
- ✅ Python 3.12+ compliance
- ✅ FastAPI 0.115.x patterns
- ✅ Pydantic 2.x validation
- ✅ SQLAlchemy 2.0 async patterns
- ✅ Type hints with modern syntax (dict[str, int] not Dict[str, int])
- ✅ Exception chaining (B904 compliance)
- ✅ Code complexity A/B ratings (target ≤10, warn >15, error >20)
- ✅ Maintainability index ≥65 (B grade minimum)
- ✅ Code duplication <3%
- ✅ Ruff linting compliance
- ✅ mypy strict type checking
- ✅ Performance maintained or improved

### 6.3 Quality
- ✅ Documentation complete
- ✅ Error handling comprehensive
- ✅ Logging structured and useful
- ✅ Health checks comprehensive

---

## 7. Risk Mitigation

### 7.1 Risks
1. **Breaking Changes**: Risk of breaking existing functionality
2. **Performance Impact**: Risk of performance degradation
3. **Integration Issues**: Risk of integration problems with HA AI Agent Service

### 7.2 Mitigation
1. **Incremental Updates**: Update one component at a time
2. **Comprehensive Testing**: Test each change thoroughly
3. **Backward Compatibility**: Maintain backward compatibility
4. **Staged Rollout**: Deploy to staging first, then production

---

## 8. Dependencies

### 8.1 External Dependencies
- HA AI Agent Service (Port 8030) - Must be running
- Weather API Service (Port 8009)
- Sports Data Service (Port 8005)
- Carbon Intensity Service (Port 8010)
- Data API Service (Port 8006)

### 8.2 Internal Dependencies
- Shared logging configuration
- Shared database patterns
- Shared configuration patterns

---

## 9. Timeline

**Total Estimated Effort:** 30-40 hours (4 weeks)

- **Week 1:** Core Updates (10-14 hours)
- **Week 2:** Context & Prompt Enhancements (10-14 hours)
- **Week 3:** Configuration & Infrastructure (7-10 hours)
- **Week 4:** Metadata & Documentation (8-10 hours)

---

## 10. Next Steps

1. **Review Plan**: Review this plan with team
2. **Prioritize Stories**: Confirm priority of stories
3. **Create Stories**: Create detailed stories in project management system
4. **Start Implementation**: Begin with Phase 1, Story 1
5. **Track Progress**: Track progress against this plan

---

## Appendix A: File Change Summary

### Files to Create
- `services/proactive-agent-service/src/services/health_check_service.py`
- `services/proactive-agent-service/src/utils/token_counter.py`
- `services/proactive-agent-service/docs/API_DOCUMENTATION.md`
- `services/proactive-agent-service/docs/ENVIRONMENT_VARIABLES.md`

### Files to Update
- `services/proactive-agent-service/src/clients/ha_agent_client.py`
- `services/proactive-agent-service/src/services/prompt_generation_service.py`
- `services/proactive-agent-service/src/services/suggestion_pipeline_service.py`
- `services/proactive-agent-service/src/services/suggestion_storage_service.py`
- `services/proactive-agent-service/src/config.py`
- `services/proactive-agent-service/src/models.py`
- `services/proactive-agent-service/src/main.py`
- `services/proactive-agent-service/src/api/health.py`
- `services/proactive-agent-service/README.md`

### Files to Reference (from ha-ai-agent-service)
- `services/ha-ai-agent-service/src/utils/token_counter.py` (copy)
- `services/ha-ai-agent-service/src/services/health_check_service.py` (reference)
- `services/ha-ai-agent-service/src/clients/ha_client.py` (reference for patterns)

---

---

## 11. 2025 Standards Compliance Checklist

### Technology Stack ✅
- [x] Python 3.12+ (not 3.11+)
- [x] FastAPI 0.115.x
- [x] Pydantic 2.x (SettingsConfigDict pattern)
- [x] SQLAlchemy 2.0 async (Mapped, mapped_column)
- [x] Type hints with modern syntax (dict[str, int], not Dict[str, int])
- [x] `from __future__ import annotations` for forward references

### Code Quality Standards ✅
- [x] Code complexity target: A/B ratings (≤10, warn >15, error >20)
- [x] Maintainability index: ≥65 (B grade minimum)
- [x] Code duplication: <3% target
- [x] Exception chaining: B904 compliance (preserve exception context)
- [x] Path handling: pathlib.Path (not os.path)
- [x] Async/await: All I/O operations async

### Testing Standards ✅
- [x] pytest 8.0+ with pytest-asyncio
- [x] Test coverage target: >90%
- [x] Test file pattern: `test_*.py`
- [x] Async test decorator: `@pytest.mark.asyncio`
- [x] Fixtures for common setup

### Logging Standards ✅
- [x] Structured logging with correlation IDs
- [x] Shared logging configuration
- [x] Proper log levels (DEBUG, INFO, WARNING, ERROR)
- [x] Exception logging with exc_info=True

### Documentation Standards ✅
- [x] Google/NumPy style docstrings
- [x] Type information in docstrings
- [x] Parameter and return type documentation
- [x] Exception documentation (Raises section)

### Code Review Standards ✅
- [x] Review scope: 200-400 LoC per session
- [x] Automated checks first (Ruff, mypy)
- [x] Time-boxed: 60-90 minutes
- [x] Risk-based prioritization
- [x] Actionable feedback

---

## 12. BMAD Story Creation Requirements

### Story Breakdown
This plan should be broken down into BMAD stories following this structure:

1. **Epic Creation** (by PM/PO)
   - Epic title: "Epic AI-XX: Proactive Agent Service - Alignment with HA AI Agent Service"
   - Epic description with business value
   - Dependencies and risks

2. **Story Creation** (by SM)
   - Each phase becomes a story
   - Stories follow BMAD story template
   - Acceptance criteria from plan
   - Dev Agent Record sections included

3. **Story Assignment** (by PO)
   - Stories assigned to sprints
   - Priority confirmed
   - Dependencies tracked

### Story Template Requirements
Each story must include:
- **Story Title:** Clear, descriptive
- **Acceptance Criteria:** From plan sections
- **Dev Notes:** Technical implementation details
- **Testing:** Test requirements
- **Dev Agent Record:** For dev agent updates
- **File List:** Tracked during implementation
- **Change Log:** Updated during implementation

---

**Document Status:** ✅ 2025 Standards Verified - Ready for BMAD Review  
**Last Updated:** December 2025  
**Reviewed By:** Dev Agent (James)  
**Next Steps:** 
1. Architect review for architecture alignment
2. QA review for testing strategy
3. PO review for story breakdown
4. Story creation by SM agent

