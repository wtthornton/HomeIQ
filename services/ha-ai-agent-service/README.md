# HA AI Agent Service

**Port:** 8030  
**Technology:** Python 3.12+, FastAPI 0.115.x, SQLAlchemy 2.0  
**Purpose:** Conversational AI Agent for Home Assistant Automation Creation  
**Status:** ✅ Production Ready (Epic AI-20 Complete)

## Overview

The HA AI Agent Service is a full-featured conversational AI agent that enables natural language interaction with Home Assistant. Users can describe automations in plain English, and the agent creates Home Assistant automations using OpenAI's GPT-4o/GPT-4o-mini models with function calling capabilities.

### Key Features

- **Conversational Interface**: Full chat API with conversation persistence and history management
- **Context-Aware**: Automatically injects Tier 1 context (entities, areas, services, capabilities) into every conversation
- **Automation Creation**: Single unified tool (`create_automation_from_prompt`) that validates and creates Home Assistant automations
- **OpenAI Integration**: Full integration with OpenAI API including retry logic, rate limiting, and token budget management
- **Conversation Management**: SQLite-backed conversation persistence with message history, state management, and TTL-based cleanup
- **Token Management**: Intelligent token counting and budget enforcement with conversation history truncation
- **Health Monitoring**: Comprehensive health checks for all dependencies

## Epic AI-20: HA AI Agent Service - Completion & Production Readiness ✅ **COMPLETE**

The service is now production-ready with full conversational AI capabilities, comprehensive testing, and complete documentation.

### Epic AI-19: Tier 1 Context Injection ✅ **COMPLETE**

This epic implemented the foundational context injection system with the following components:

1. **Entity Inventory Summary** - Aggregated entity counts by domain and area
2. **Areas/Rooms List** - All areas from Home Assistant
3. **Available Services Summary** - Services by domain with common parameters
4. **Device Capability Patterns** - Capability examples from device intelligence
5. **Helpers & Scenes Summary** - Available helpers and scenes for reusable components
6. **Context Builder** - Orchestrates all components and formats for OpenAI
7. **System Prompt** - Defines agent role, behavior, and automation creation guidelines

## Architecture

### Service Components

1. **Context Builder** - Orchestrates Tier 1 context injection:
   - Entity inventory summaries (cached 5 min)
   - Areas/rooms list (cached 10 min)
   - Available services summary (cached 10 min)
   - Device capability patterns (cached 15 min)
   - Helpers & scenes summary (cached 10 min)

2. **Conversation Service** - Manages conversation state:
   - Conversation creation and persistence
   - Message history management
   - Context caching per conversation (5 min TTL)
   - Conversation state (ACTIVE/ARCHIVED)
   - TTL-based cleanup (default 30 days)

3. **Prompt Assembly Service** - Assembles prompts for OpenAI:
   - System prompt with Tier 1 context injection
   - Conversation history management
   - Token counting and budget enforcement (16k token limit)
   - Generic message filtering
   - User request emphasis

4. **OpenAI Client** - Handles OpenAI API interactions:
   - Async chat completions with function calling
   - Retry logic with exponential backoff
   - Rate limiting handling (429 errors)
   - Token tracking and statistics
   - Error handling and recovery

5. **Tool Service** - Executes OpenAI function calls:
   - Single tool: `create_automation_from_prompt`
   - YAML validation
   - Home Assistant automation creation
   - Error handling and reporting

### Technology Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM for database operations
- **SQLite** - Database for conversation persistence and context caching
- **OpenAI Python SDK** - Official OpenAI API client
- **Pydantic** - Settings and data validation
- **Tenacity** - Retry logic for API calls

## API Endpoints

### Chat Endpoints

**POST** `/api/v1/chat` - Main chat endpoint for interacting with the AI agent
- Accepts user messages and returns AI responses
- Supports multi-turn conversations with history
- Handles OpenAI function calling for automation creation
- Rate limited: 100 requests/minute per IP

**Request:**
```json
{
  "message": "Turn on the kitchen lights when motion is detected",
  "conversation_id": "optional-conversation-id",
  "refresh_context": false
}
```

**Response:**
```json
{
  "message": "I'll create an automation that turns on the kitchen lights when motion is detected...",
  "conversation_id": "conv-123",
  "tool_calls": [
    {
      "id": "call_abc123",
      "name": "create_automation_from_prompt",
      "arguments": {
        "user_prompt": "...",
        "automation_yaml": "...",
        "alias": "..."
      }
    }
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "tokens_used": 1234,
    "response_time_ms": 2345,
    "iterations": 2
  }
}
```

### Conversation Management Endpoints

**GET** `/api/v1/conversations` - List conversations (paginated, filterable)
**GET** `/api/v1/conversations/{id}` - Get conversation with full message history
**POST** `/api/v1/conversations` - Create new conversation
**DELETE** `/api/v1/conversations/{id}` - Delete conversation

### Context Endpoints (Development/Debug)

**GET** `/api/v1/context` - Get Tier 1 context (formatted for OpenAI)
**GET** `/api/v1/system-prompt` - Get base system prompt
**GET** `/api/v1/complete-prompt` - Get complete system prompt with context

### Tool Endpoints

**GET** `/api/v1/tools` - Get available tool schemas
**POST** `/api/v1/tools/execute` - Execute a tool call (direct)
**POST** `/api/v1/tools/execute-openai` - Execute a tool call (OpenAI format)

### Health Check

**GET** `/health` - Comprehensive health check for all dependencies

## Configuration

### Required Environment Variables

- `HA_TOKEN` - Home Assistant long-lived access token (required)
- `OPENAI_API_KEY` - OpenAI API key (required for chat functionality)

### Optional Environment Variables

**Service Configuration:**
- `SERVICE_PORT` - Service port (default: `8030`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

**Home Assistant:**
- `HA_URL` - Home Assistant URL (default: `http://homeassistant:8123`)
- `HA_TIMEOUT` - Request timeout in seconds (default: `10`)
- `HA_MAX_RETRIES` - Maximum retry attempts (default: `3`)

**External Services:**
- `DATA_API_URL` - Data API service URL (default: `http://data-api:8006`)
- `DEVICE_INTELLIGENCE_URL` - Device Intelligence Service URL (default: `http://device-intelligence-service:8019`)
- `DEVICE_INTELLIGENCE_ENABLED` - Enable device intelligence (default: `true`)

**OpenAI:**
- `OPENAI_MODEL` - Model to use: `gpt-4o` or `gpt-4o-mini` (default: `gpt-4o-mini`)
- `OPENAI_MAX_TOKENS` - Maximum tokens for responses (default: `4096`)
- `OPENAI_TEMPERATURE` - Temperature 0.0-2.0 (default: `0.7`)
- `OPENAI_TIMEOUT` - API timeout in seconds (default: `30`)
- `OPENAI_MAX_RETRIES` - Maximum retry attempts (default: `3`)

**Database:**
- `DATABASE_URL` - SQLite database URL (default: `sqlite+aiosqlite:///./data/ha_ai_agent.db`)
- `CONVERSATION_TTL_DAYS` - Conversation TTL in days (default: `30`)

**CORS:**
- `HA_AI_AGENT_ALLOWED_ORIGINS` - Comma-delimited allowed origins (default: `http://localhost:3000,http://localhost:3001`)

See [Environment Variables Documentation](docs/ENVIRONMENT_VARIABLES.md) for complete details.

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

### Epic AI-19: Tier 1 Context Injection ✅ Complete
- **AI19.1** ✅ Service Foundation & Context Builder Structure
- **AI19.2** ✅ Entity Inventory Summary Service
- **AI19.3** ✅ Areas/Rooms List Service
- **AI19.4** ✅ Available Services Summary Service
- **AI19.5** ✅ Device Capability Patterns Service
- **AI19.6** ✅ Helpers & Scenes Summary Service

### Epic AI-20: Completion & Production Readiness ✅ Complete
- **AI20.1** ✅ OpenAI Client Integration
- **AI20.2** ✅ Conversation Service Foundation
- **AI20.3** ✅ Prompt Assembly & Context Integration
- **AI20.4** ✅ Chat API Endpoints
- **AI20.5** ✅ Conversation Management API
- **AI20.6** ✅ Conversation Persistence
- **AI20.7** ✅ HA Agent Chat Page
- **AI20.8** ✅ Conversation Management UI
- **AI20.9** ✅ Tool Call Visualization
- **AI20.10** ✅ Automation Preview & Creation
- **AI20.11** ✅ Comprehensive Testing
- **AI20.12** ✅ Production Readiness & Documentation

## Dependencies

- `data-api` (Port 8006) - Entity and device queries
- `device-intelligence-service` (Port 8028) - Device capability discovery
- Home Assistant REST API - Areas, services, sun info

## Database

SQLite database (`ha_ai_agent.db`) stores:

### Context Cache (TTL-based expiration)
- Entity summaries (5 min TTL)
- Areas list (10 min TTL)
- Services summary (10 min TTL)
- Capability patterns (15 min TTL)
- Helpers & scenes summary (10 min TTL)

### Conversation Persistence
- Conversations table: conversation metadata, state, timestamps
- Messages table: full message history per conversation
- Context cache per conversation (5 min TTL, refreshed on new messages)
- Automatic cleanup of conversations older than TTL (default: 30 days)

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
- **Chat Response Time**: < 3 seconds ✅ (includes OpenAI API call + tool execution)
- **Token Budget**: 16,000 input tokens (with automatic history truncation)
- **Rate Limiting**: 100 requests/minute per IP address

