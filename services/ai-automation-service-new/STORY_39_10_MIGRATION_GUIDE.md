# Story 39.10 Migration Guide

## Status: Foundation Complete ✅

The foundation for `ai-automation-service-new` has been created with:
- ✅ 2025 FastAPI patterns (async/await, dependency injection)
- ✅ Authentication middleware
- ✅ Rate limiting middleware
- ✅ Database connection pooling (async SQLAlchemy 2.0)
- ✅ Proper project structure
- ✅ Pydantic v2 models

## Remaining Work

### 1. Client Services (High Priority)

Create HTTP clients for external services:

**Files to create:**
- `src/clients/data_api_client.py` - Data API client (fetch devices, entities)
- `src/clients/ha_client.py` - Home Assistant client (deploy automations)
- `src/clients/openai_client.py` - OpenAI client (YAML generation)

**Reference:** `services/ai-automation-service/src/clients/`

### 2. Core Services (High Priority)

Migrate core business logic:

**Suggestion Generation Service:**
- `src/services/suggestion_service.py`
- Reference: `services/ai-automation-service/src/api/suggestion_router.py` (lines 1-1680)
- Key functions to migrate:
  - `generate_suggestions()` - Main generation logic
  - `list_suggestions()` - List with filtering
  - `get_usage_stats()` - Usage statistics

**YAML Generation Service:**
- `src/services/yaml_generation_service.py`
- Reference: `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- Key functions:
  - `generate_automation_yaml()` - Main YAML generation
  - `pre_validate_suggestion_for_yaml()` - Pre-validation
  - `build_suggestion_specific_entity_mapping()` - Entity mapping

**Deployment Service:**
- `src/services/deployment_service.py`
- Reference: `services/ai-automation-service/src/api/deployment_router.py`
- Key functions:
  - `deploy_suggestion()` - Deploy to Home Assistant
  - `batch_deploy()` - Batch deployment
  - `rollback_automation()` - Version rollback
  - `get_automation_status()` - Status checking

**Safety Validation Service:**
- `src/services/safety_validator.py`
- Reference: `services/ai-automation-service/src/safety_validator.py`
- 6-rule safety engine

### 3. Update Routers (Medium Priority)

Update routers to use migrated services:

**Suggestion Router:**
- Update `src/api/suggestion_router.py` to call `SuggestionService`
- Add proper error handling
- Add request/response models (Pydantic v2)

**Deployment Router:**
- Update `src/api/deployment_router.py` to call `DeploymentService`
- Add proper error handling
- Add request/response models

### 4. Database Models (Medium Priority)

Ensure all required models are available:

**Check:**
- `Suggestion` model (✅ exists)
- `AutomationVersion` model (✅ exists)
- Additional models if needed from original service

**Reference:** `services/ai-automation-service/src/database/models.py`

### 5. Integration Tests (High Priority)

Create comprehensive tests:

**Test files:**
- `tests/test_suggestion_service.py`
- `tests/test_yaml_generation_service.py`
- `tests/test_deployment_service.py`
- `tests/test_integration.py`

**Test coverage:**
- Unit tests for each service
- Integration tests for API endpoints
- Error handling tests
- Rate limiting tests
- Authentication tests

### 6. Docker Configuration (Low Priority)

Update docker-compose.yml:

**Add service:**
```yaml
ai-automation-service-new:
  build:
    context: ./services/ai-automation-service-new
    dockerfile: Dockerfile
  container_name: ai-automation-service-new
  ports:
    - "8025:8025"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
    - DATA_API_URL=http://data-api:8006
    - HA_URL=${HA_URL}
    - HA_TOKEN=${HA_TOKEN}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  volumes:
    - ./services/ai-automation-service/data:/app/data:rw
  depends_on:
    - data-api
```

### 7. Documentation (Low Priority)

Update documentation:

- Update `README.md` with complete API documentation
- Add migration notes
- Update architecture diagrams
- Add deployment guide

## Migration Strategy

### Phase 1: Client Services (1-2 hours)
1. Create HTTP clients
2. Add retry logic
3. Add error handling
4. Add tests

### Phase 2: Core Services (4-6 hours)
1. Migrate suggestion generation
2. Migrate YAML generation
3. Migrate deployment logic
4. Add safety validation
5. Add tests

### Phase 3: Integration (2-3 hours)
1. Update routers
2. Add request/response models
3. Add error handling
4. Integration tests

### Phase 4: Deployment (1 hour)
1. Update docker-compose.yml
2. Test in Docker environment
3. Update documentation

## Key Patterns to Follow

### 2025 FastAPI Patterns

1. **Dependency Injection:**
```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
```

2. **Pydantic v2 Models:**
```python
from pydantic import BaseModel, Field, ConfigDict

class RequestModel(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True
    )
    field: str = Field(..., min_length=1)
```

3. **Async/Await:**
```python
async def service_method(db: DatabaseSession) -> ResponseModel:
    result = await db.execute(query)
    return ResponseModel.from_orm(result)
```

4. **Error Handling:**
```python
from fastapi import HTTPException, status

if not result:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Resource not found"
    )
```

## Next Steps

1. **Immediate:** Create client services (data_api_client, ha_client, openai_client)
2. **Next:** Migrate suggestion generation service
3. **Then:** Migrate YAML generation service
4. **Finally:** Migrate deployment service

## Notes

- All services should use async/await patterns
- All database operations should use async SQLAlchemy 2.0
- All HTTP clients should use httpx (async)
- All models should use Pydantic v2
- All endpoints should have proper error handling
- All services should be testable (dependency injection)

