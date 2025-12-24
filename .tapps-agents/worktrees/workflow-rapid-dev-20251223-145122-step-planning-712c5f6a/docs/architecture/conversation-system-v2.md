# Conversation System v2 Architecture

**Last Updated:** January 2025  
**Status:** Production Ready

## Overview

The v2 Conversation System is a complete redesign of the AI automation authoring system, transforming a 7,200-line monolithic router into a modular, maintainable architecture.

## Architecture Principles

1. **Modularity** - Services are organized into focused modules
2. **Dependency Injection** - ServiceContainer eliminates global state
3. **Separation of Concerns** - Clear boundaries between entity, automation, and conversation services
4. **Explicit Response Types** - Clear distinction between automation, action, and information
5. **Conversation-Centric** - Persistent conversation IDs enable multi-turn interactions

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ AskAI.tsx    │  │ ResponseHandler│  │ useConversationV2│ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │  api-v2.ts     │                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────▼─────────────────────────────────┐
│                  API Layer (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Conversation │  │  Automation  │  │    Action    │     │
│  │   Router     │  │    Router    │  │    Router    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │ ServiceContainer│                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                    Service Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Entity     │  │  Automation  │  │ Conversation │     │
│  │  Services    │  │   Services   │  │   Services   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│  ┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐     │
│  │ Extractor   │  │ YAML Gen     │  │ Context Mgr  │     │
│  │ Validator   │  │ Validator    │  │ Intent Match │     │
│  │ Enricher    │  │ Corrector    │  │ Response Bld │     │
│  │ Resolver    │  │ Test Exec    │  │ History Mgr  │     │
│  └─────────────┘  │ Deployer     │  └──────────────┘     │
│                   └──────────────┘                        │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │  Confidence  │  │ Error        │                      │
│  │  Calculator  │  │ Recovery     │                      │
│  └──────────────┘  └──────────────┘                      │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │  Function    │  │   Device     │                      │
│  │  Registry    │  │   Context    │                      │
│  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   InfluxDB   │  │   SQLite     │  │  Home        │     │
│  │  (Events)    │  │  (Metadata)  │  │  Assistant   │     │
│  └──────────────┘  └──────┬───────┘  └──────┬───────┘     │
│                            │                  │              │
│                    ┌───────▼────────┐                        │
│                    │  v2 Database   │                        │
│                    │  - conversations│                        │
│                    │  - turns       │                        │
│                    │  - suggestions │                        │
│                    │  - confidence  │                        │
│                    └────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### ServiceContainer

Centralized dependency injection container. All services are accessed via the container:

```python
from ...services.service_container import get_service_container

container = get_service_container()
entities = await container.entity_extractor.extract(query)
```

**Benefits:**
- Eliminates global variables
- Lazy initialization
- Easy testing (mock container)
- Single source of truth

### Entity Services

**Location:** `services/entity/`

**Services:**
- `extractor.py` - Unified entity extraction (consolidates 3 services)
- `validator.py` - Unified entity validation (consolidates 3 services)
- `enricher.py` - Unified entity enrichment (consolidates 2 services)
- `resolver.py` - Device name to entity ID resolution

**Flow:**
```
Query → Extractor → Validator → Enricher → Resolver → Validated Entities
```

### Automation Services

**Location:** `services/automation/`

**Services:**
- `yaml_generator.py` - Generate automation YAML
- `yaml_validator.py` - Multi-stage validation (5 stages)
- `yaml_corrector.py` - Self-correction service
- `test_executor.py` - Test automation before deployment
- `deployer.py` - Deploy to Home Assistant

**Flow:**
```
Suggestion → Generator → Validator → Corrector → Test → Deploy
```

### Conversation Services

**Location:** `services/conversation/`

**Services:**
- `context_manager.py` - Manage conversation context
- `intent_matcher.py` - Match user intent (automation/action/info)
- `response_builder.py` - Build structured responses
- `history_manager.py` - Manage conversation history

**Flow:**
```
Message → Intent Matcher → Context Manager → Response Builder → History Manager
```

### Confidence Calculator

**Location:** `services/confidence/calculator.py`

**Features:**
- Multi-factor confidence scoring
- Factor breakdown (entity_resolution, intent_clarity, context_relevance)
- Explanation generation
- Threshold-based decision making

### Error Recovery

**Location:** `services/error_recovery.py`

**Features:**
- Structured error responses
- Actionable recovery guidance
- Handles: NoEntitiesFoundError, AmbiguousQueryError, ValidationError

### Function Registry

**Location:** `services/function_calling/registry.py`

**Supported Functions:**
- `turn_on_light`, `turn_off_light`, `set_light_brightness`
- `turn_on_switch`, `turn_off_switch`
- `get_entity_state`, `set_temperature`
- `lock_door`, `unlock_door`

### Device Context Service

**Location:** `services/device/context_service.py`

**Features:**
- Real-time device state enrichment
- Usage pattern analysis (framework ready)
- Response rate calculation (framework ready)

## API Endpoints

### Conversation API

- `POST /api/v2/conversations` - Start conversation
- `POST /api/v2/conversations/{id}/message` - Send message
- `GET /api/v2/conversations/{id}` - Get conversation
- `GET /api/v2/conversations/{id}/suggestions` - Get suggestions
- `POST /api/v2/conversations/{id}/stream` - Stream conversation turn

### Action API

- `POST /api/v2/actions/execute` - Execute immediate action

### Automation API

- `POST /api/v2/automations/generate` - Generate automation
- `POST /api/v2/automations/test` - Test automation
- `POST /api/v2/automations/deploy` - Deploy automation
- `GET /api/v2/automations` - List automations

## Database Schema

### conversations

```sql
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    initial_query TEXT NOT NULL,
    context TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT
);
```

### conversation_turns

```sql
CREATE TABLE conversation_turns (
    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    response_type TEXT NOT NULL,
    response_content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);
```

### confidence_factors

```sql
CREATE TABLE confidence_factors (
    factor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    factor_name TEXT NOT NULL,
    factor_value REAL NOT NULL,
    FOREIGN KEY (turn_id) REFERENCES conversation_turns(turn_id)
);
```

### function_calls

```sql
CREATE TABLE function_calls (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    function_name TEXT NOT NULL,
    parameters TEXT NOT NULL,
    result TEXT,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    FOREIGN KEY (turn_id) REFERENCES conversation_turns(turn_id)
);
```

### automation_suggestions_v2

```sql
CREATE TABLE automation_suggestions_v2 (
    suggestion_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    automation_yaml TEXT,
    confidence REAL NOT NULL,
    validated_entities TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
    FOREIGN KEY (turn_id) REFERENCES conversation_turns(turn_id)
);
```

## Data Flow

### Conversation Flow

```
1. User sends query
   ↓
2. Start conversation (POST /api/v2/conversations)
   ↓
3. Intent matcher determines type (automation/action/info)
   ↓
4. Entity extractor extracts entities
   ↓
5. Entity validator validates entities
   ↓
6. Entity enricher enriches with metadata
   ↓
7. Entity resolver resolves to entity IDs
   ↓
8. Confidence calculator calculates confidence
   ↓
9. Response builder builds response
   ↓
10. History manager saves turn
    ↓
11. Return response to user
```

### Automation Generation Flow

```
1. User approves suggestion
   ↓
2. YAML generator generates automation YAML
   ↓
3. YAML validator validates (5 stages)
   ↓
4. If invalid, YAML corrector attempts correction
   ↓
5. Test executor tests automation
   ↓
6. If test passes, deployer deploys to HA
   ↓
7. Return deployment result
```

### Action Execution Flow

```
1. User requests immediate action
   ↓
2. Intent matcher identifies as action
   ↓
3. Entity extractor extracts target entity
   ↓
4. Function registry calls appropriate function
   ↓
5. Execute Home Assistant service
   ↓
6. Return execution result
```

## Response Types

### automation_generated

- Contains `suggestions` array
- User should review and approve/reject
- May contain `confidence` breakdown

### clarification_needed

- Contains `clarification_questions` array
- User should answer questions
- Improves confidence for next turn

### action_done

- Action was executed immediately
- Contains `result` with execution details
- No automation created

### information_provided

- Informational response
- No action taken
- Contains `content` with information

### error

- Error occurred during processing
- Contains `content` with error message
- May contain `next_actions` with recovery suggestions

### no_intent_match

- Could not determine user intent
- Contains `content` with explanation
- May contain `next_actions` with suggestions

## Performance Considerations

### Caching

- Entity extraction results cached
- Device metadata cached
- Validation results cached

### Database Indexes

- `conversations(user_id, created_at)`
- `conversation_turns(conversation_id, turn_number)`
- `automation_suggestions_v2(conversation_id, status)`

### Async Operations

- All I/O operations are async
- Database queries use async SQLAlchemy
- HTTP requests use async httpx

## Security

### Authentication

- All endpoints require API key
- Bearer token or X-HomeIQ-API-Key header

### Input Validation

- Pydantic models validate all inputs
- SQL injection prevention via parameterized queries
- XSS prevention via output encoding

### Rate Limiting

- Conversation creation: 10/min per user
- Message sending: 30/min per conversation
- Action execution: 60/min per user

## Monitoring

### Metrics

- Conversation creation rate
- Message processing time
- Suggestion generation time
- Error rates by type
- Confidence score distribution

### Logging

- Structured logging with correlation IDs
- Request/response logging
- Error stack traces
- Performance metrics

## Testing

### Unit Tests

- Service-level unit tests
- Mock external dependencies
- Fast execution (< 1s per test)

### Integration Tests

- API endpoint tests
- Database integration tests
- End-to-end flow tests

### Performance Tests

- Latency benchmarks
- Throughput measurements
- Concurrent request handling

## Future Enhancements

1. **Multi-language support** - Support for non-English queries
2. **Voice interface** - Speech-to-text integration
3. **Advanced analytics** - Usage patterns and insights
4. **Collaborative editing** - Multiple users editing automations
5. **Template library** - Pre-built automation templates
6. **AI model fine-tuning** - Custom models per user

## Migration from v1

See [Migration Guide](../migration/v1-to-v2-migration-guide.md) for detailed migration instructions.

## References

- [API Documentation](../api/v2/conversation-api.md)
- [Migration Guide](../migration/v1-to-v2-migration-guide.md)
- [Quick Start Guide](../../implementation/HA_CONVERSATION_QUICK_START.md)

