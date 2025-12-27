# Context7 Telemetry Pattern for HomeIQ

**Status:** Implemented  
**Date:** 2025-01-XX  
**Based On:** Context7 FastAPI Best Practices  

## Decision

Implement telemetry using Context7 recommended patterns:
- Singleton global state (with setter functions for injection)
- FastAPI dependency injection patterns
- Pydantic settings for configuration

## Context7 Best Practices Applied

### 1. Global State with Setter Pattern

**Source:** Context7 FastAPI Documentation - Dependency Injection

```python
# ✅ CORRECT (Context7 Pattern)
_multi_model_extractor = None

def set_multi_model_extractor(extractor):
    """Set extractor reference for stats endpoint"""
    global _multi_model_extractor
    _multi_model_extractor = extractor

def get_multi_model_extractor():
    """Get extractor instance"""
    return _multi_model_extractor
```

**Why:** Avoids circular dependencies, allows late binding, easy to test

### 2. Pydantic Settings Pattern

**Source:** `docs/kb/context7-cache/fastapi-pydantic-settings.md`

```python
class Settings(BaseSettings):
    entity_extraction_method: str = "multi_model"
    ner_model: str = "dslim/bert-base-NER"
    
    model_config = SettingsConfigDict(env_file=".env")
Consequence
```

**Why:** Type validation, defaults, environment variable support

### 3. Singleton with lru_cache

**Source:** Context7 FastAPI Examples

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

**Why:** Settings loaded once, reused across requests

## Implementation

### Architecture

```
main.py (startup)
    ↓
    Calls set_multi_model_extractor(_multi_model_extractor)
        ↓
health.py (_multi_model_extractor global)
    ↓
    /stats endpoint reads from _multi_model_extractor.stats
```

### Key Files

1. **services/ai-automation-service/src/api/ask_ai_router.py**
   - Global: `_multi_model_extractor`
   - Functions: `set_device_intelligence_client()`, `get_multi_model_extractor()`

2. **services/ai-automation-service/src/api/health.py**
   - Global: `_multi_model_extractor` (imported)
   - Functions: `set_multi_model_extractor()`
   - Endpoint: `GET /stats`

3. **services/ai-automation-service/src/main.py**
   - Calls: `set_multi_model_extractor(extractor)` on startup

## Testing Pattern

### Context7 Testing with Override

```python
# Override for testing
def get_multi_model_extractor_override():
    return MockMultiModelExtractor()

app.dependency_overrides[get_multi_model_extractor] = get_multi_model_extractor_override
```

## Alternatives Considered

1. **Pure dependency injection** - Rejected (too complex for global state)
2. **Database storage** - Rejected (not needed for stats, adds latency)
3. **Context7 Pattern** - Accepted ✅

## References

- Context7: `/fastapi/fastapi` - Dependency Injection
- KB: `docs/kb/context7-cache/fastapi-pydantic-settings.md`
- KB: `docs/kb/context7-cache/simple-config-management-pattern.md`

