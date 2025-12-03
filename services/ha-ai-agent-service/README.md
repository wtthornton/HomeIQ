# HA AI Agent Service

**Port:** 8030  
**Technology:** Python 3.12+, FastAPI 0.115.x, SQLAlchemy 2.0  
**Purpose:** Tier 1 Context Injection for Home Assistant AI Agent  
**Status:** ✅ Complete (Epic AI-19)

## Overview

The HA AI Agent Service provides foundational context injection for a conversational AI agent that interacts with Home Assistant. This service implements Tier 1 essential context that is always included in every conversation to enable efficient automation generation without excessive tool calls.

## Epic AI-19: Tier 1 Context Injection

This epic implements the foundational context injection system with the following components:

1. **Entity Inventory Summary** - Aggregated entity counts by domain and area
2. **Areas/Rooms List** - All areas from Home Assistant
3. **Available Services Summary** - Services by domain with common parameters
4. **Device Capability Patterns** - Capability examples from device intelligence
5. **Helpers & Scenes Summary** - Available helpers and scenes for reusable components
6. **Context Builder** - Orchestrates all components and formats for OpenAI
7. **System Prompt** - Defines agent role, behavior, and automation creation guidelines

## Architecture

- **Standalone Service** - Follows Epic 31 pattern (direct HA API calls)
- **SQLite Cache** - Context caching for performance (TTL-based)
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM for database operations

## API Endpoints

### Health Check
```
GET /health
```

### Get Context
```
GET /api/v1/context
```

Returns Tier 1 context formatted for OpenAI agent.

### Get System Prompt
```
GET /api/v1/system-prompt
```

Returns the base system prompt defining the agent's role and behavior.

### Get Complete Prompt
```
GET /api/v1/complete-prompt
```

Returns the complete system prompt with Tier 1 context injected, ready for OpenAI API calls.

## Configuration

Environment variables:
- `HA_URL` - Home Assistant URL (default: `http://homeassistant:8123`)
- `HA_TOKEN` - Home Assistant long-lived access token
- `DATA_API_URL` - Data API service URL (default: `http://data-api:8006`)
- `DEVICE_INTELLIGENCE_URL` - Device Intelligence Service URL
- `OPENAI_API_KEY` - OpenAI API key (optional for now)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Development

### Setup
```bash
cd services/ha-ai-agent-service
pip install -r requirements.txt
```

### Run Tests
```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/ -m "not integration"

# Run integration tests (requires services)
pytest tests/integration/ -m integration

# Run performance tests
pytest tests/test_performance.py

# Check test coverage
pytest tests/ --cov=src --cov-report=html
```

### Run Service
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload
```

## Stories

- **AI19.1** ✅ Service Foundation & Context Builder Structure
- **AI19.2** ✅ Entity Inventory Summary Service
- **AI19.3** ✅ Areas/Rooms List Service
- **AI19.4** ✅ Available Services Summary Service
- **AI19.5** ✅ Device Capability Patterns Service
- **AI19.6** ✅ Helpers & Scenes Summary Service

**Epic AI-19 Status:** ✅ Complete

## Dependencies

- `data-api` (Port 8006) - Entity and device queries
- `device-intelligence-service` (Port 8028) - Device capability discovery
- Home Assistant REST API - Areas, services, sun info

## Database

SQLite database (`ha_ai_agent.db`) stores context cache with TTL-based expiration:
- Entity summaries (5 min TTL)
- Areas list (10 min TTL)
- Services summary (10 min TTL)
- Capability patterns (15 min TTL)
- Helpers & scenes summary (10 min TTL)

## Testing

### Test Coverage
- **Unit Tests**: All services and clients have comprehensive unit tests (>90% coverage)
- **Integration Tests**: Tests for context builder with external services
- **End-to-End Tests**: Complete chat flow tests
- **Performance Tests**: Verify performance requirements (<100ms with cache, <3s chat response)

### Test Structure
- `tests/test_*.py` - Unit tests for individual services and clients
- `tests/integration/` - Integration tests requiring external services
- `tests/test_performance.py` - Performance benchmarks
- `tests/test_chat_performance.py` - Chat endpoint performance tests

### Running Tests
See [Test Documentation](tests/README.md) for comprehensive testing guide.

## Documentation

### Core Documentation
- [API Documentation](docs/API_DOCUMENTATION.md) - Complete API reference
- [System Prompt](docs/SYSTEM_PROMPT.md) - System prompt details
- [Test Documentation](tests/README.md) - Testing guide and examples

### Production Documentation
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) - Configuration guide
- [Deployment Guide](docs/DEPLOYMENT.md) - Docker and docker-compose deployment
- [Error Handling](docs/ERROR_HANDLING.md) - Error codes and troubleshooting
- [Monitoring Guide](docs/MONITORING.md) - Health checks and monitoring
- [Security Review](docs/SECURITY.md) - Security best practices
- [Performance Benchmarks](docs/PERFORMANCE.md) - Performance targets and optimization

## Performance Requirements

- **Context Building (with cache)**: < 100ms ✅
- **Context Building (first call)**: < 500ms ✅
- **System Prompt Retrieval**: < 10ms ✅
- **Complete Prompt Building**: < 100ms ✅
- **Chat Response Time**: <3 seconds ✅

