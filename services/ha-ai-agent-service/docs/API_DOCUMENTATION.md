# HA AI Agent Service API Documentation

**Version:** 1.0  
**Base URL:** `http://ha-ai-agent-service:8030`  
**Status:** ✅ Complete (Epic AI-20)

---

## Overview

The HA AI Agent Service provides a full conversational AI interface for Home Assistant automation creation. The service integrates with OpenAI's GPT-4o/GPT-4o-mini models to enable natural language automation creation, with automatic context injection and conversation persistence.

---

## Endpoints

### Chat Endpoint

**POST** `/api/v1/chat`

Main endpoint for interacting with the AI agent. Accepts user messages and returns AI responses with optional tool calls for automation creation.

**Rate Limit:** 100 requests/minute per IP address

**Request Body:**
```json
{
  "message": "Turn on the kitchen lights when motion is detected",
  "conversation_id": "optional-conversation-id",
  "refresh_context": false
}
```

**Request Fields:**
- `message` (string, required) - User message to send to the agent
- `conversation_id` (string, optional) - Existing conversation ID. If not provided, a new conversation is created
- `refresh_context` (boolean, optional) - Force refresh of Tier 1 context (default: `false`, uses cache if available)

**Response:**
```json
{
  "message": "I'll create an automation that turns on the kitchen lights when motion is detected...",
  "conversation_id": "conv-abc123",
  "tool_calls": [
    {
      "id": "call_xyz789",
      "name": "create_automation_from_prompt",
      "arguments": {
        "user_prompt": "Turn on the kitchen lights when motion is detected",
        "automation_yaml": "alias: Kitchen Motion Lights\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.kitchen_motion\n    to: 'on'\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.kitchen",
        "alias": "Kitchen Motion Lights"
      }
    }
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "tokens_used": 1234,
    "response_time_ms": 2345,
    "token_breakdown": {
      "system_tokens": 850,
      "history_tokens": 200,
      "new_message_tokens": 50,
      "total_tokens": 1100,
      "max_input_tokens": 16000,
      "within_budget": true
    },
    "iterations": 2
  }
}
```

**Response Fields:**
- `message` (string) - AI assistant response text
- `conversation_id` (string) - Conversation ID (use for subsequent messages)
- `tool_calls` (array) - List of tool calls made by the agent (if any)
- `metadata` (object) - Request metadata including token usage and performance metrics

**Tool Call Format:**
- `id` (string) - Tool call ID from OpenAI
- `name` (string) - Tool name (currently only `create_automation_from_prompt`)
- `arguments` (object) - Tool arguments including:
  - `user_prompt` - Original user request
  - `automation_yaml` - Complete automation YAML
  - `alias` - Automation name/alias

**Status Codes:**
- `200 OK` - Request processed successfully
- `400 Bad Request` - Invalid request or token budget exceeded
- `404 Not Found` - Conversation not found (if conversation_id provided)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Internal service error
- `503 Service Unavailable` - OpenAI API unavailable or rate limited

**Example:**
```bash
curl -X POST http://localhost:8030/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Turn on the kitchen lights when motion is detected"
  }'
```

**Multi-Turn Conversation:**
```bash
# First message (creates new conversation)
curl -X POST http://localhost:8030/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create an automation for kitchen lights"}'

# Response includes conversation_id: "conv-abc123"

# Follow-up message (uses existing conversation)
curl -X POST http://localhost:8030/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Actually, make it turn off after 5 minutes",
    "conversation_id": "conv-abc123"
  }'
```

---

### Conversation Management Endpoints

#### List Conversations

**GET** `/api/v1/conversations`

List conversations with pagination and filtering.

**Query Parameters:**
- `limit` (integer, optional) - Page size (1-100, default: 20)
- `offset` (integer, optional) - Offset for pagination (default: 0)
- `state` (string, optional) - Filter by state: `active` or `archived`
- `start_date` (string, optional) - Filter conversations created after this date (ISO format)
- `end_date` (string, optional) - Filter conversations created before this date (ISO format)

**Response:**
```json
{
  "conversations": [
    {
      "conversation_id": "conv-abc123",
      "state": "active",
      "message_count": 5,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:35:00Z",
      "messages": null
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

**Status Codes:**
- `200 OK` - Conversations retrieved successfully
- `400 Bad Request` - Invalid query parameters

---

#### Get Conversation

**GET** `/api/v1/conversations/{conversation_id}`

Get a conversation with full message history.

**Path Parameters:**
- `conversation_id` (string, required) - Conversation ID

**Response:**
```json
{
  "conversation_id": "conv-abc123",
  "state": "active",
  "message_count": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z",
  "messages": [
    {
      "message_id": "msg-1",
      "role": "user",
      "content": "Turn on the kitchen lights",
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "message_id": "msg-2",
      "role": "assistant",
      "content": "I'll create an automation...",
      "created_at": "2025-01-15T10:30:05Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Conversation retrieved successfully
- `404 Not Found` - Conversation not found

---

#### Create Conversation

**POST** `/api/v1/conversations`

Create a new conversation.

**Request Body:**
```json
{
  "initial_message": "Optional initial message"
}
```

**Response:**
```json
{
  "conversation_id": "conv-xyz789",
  "state": "active",
  "message_count": 1,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z",
  "messages": [
    {
      "message_id": "msg-1",
      "role": "user",
      "content": "Optional initial message",
      "created_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `201 Created` - Conversation created successfully

---

#### Delete Conversation

**DELETE** `/api/v1/conversations/{conversation_id}`

Delete a conversation and all its messages.

**Path Parameters:**
- `conversation_id` (string, required) - Conversation ID to delete

**Status Codes:**
- `204 No Content` - Conversation deleted successfully
- `404 Not Found` - Conversation not found

---

### Health Check

**GET** `/health`

Comprehensive health check endpoint that verifies all dependencies in a single call.

**Checks Performed:**
- Database connectivity
- Home Assistant connection
- Data API connection
- Device Intelligence Service connection
- OpenAI configuration
- Context builder services (all 5 components)

**Response:**
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "home_assistant": {
      "status": "healthy",
      "message": "Home Assistant connection successful",
      "entities_count": 544
    },
    "data_api": {
      "status": "healthy",
      "message": "Data API connection successful",
      "entities_available": true
    },
    "device_intelligence": {
      "status": "healthy",
      "message": "Device Intelligence Service connection successful",
      "devices_available": true
    },
    "openai": {
      "status": "healthy",
      "message": "OpenAI API key configured",
      "model": "gpt-4o-mini"
    },
    "context_builder": {
      "status": "healthy",
      "message": "Context builder operational (5/5 components available)",
      "components": {
        "entity_inventory": true,
        "areas": true,
        "services": true,
        "capability_patterns": true,
        "helpers_scenes": true
      }
    }
  },
  "summary": {
    "total": 6,
    "healthy": 6,
    "degraded": 0,
    "unhealthy": 0,
    "warnings": 0
  }
}
```

**Status Codes:**
- `200 OK` - Service is healthy or degraded (still operational)
- `503 Service Unavailable` - Service is unhealthy (critical dependencies failing)

**Status Values:**
- `healthy` - Component is working correctly
- `degraded` - Component is operational but with reduced functionality
- `unhealthy` - Component is not working
- `warning` - Component has configuration issues but may still work

**Example:**
```bash
curl http://localhost:8030/health
```

---

### Context Endpoints (Development/Debug)

These endpoints are primarily for development and debugging. In production, context is automatically injected via the chat endpoint.

#### Get Context

**GET** `/api/v1/context`

Retrieve Tier 1 context formatted for OpenAI agent.

**Response:**
```json
{
  "context": "HOME ASSISTANT CONTEXT:\nENTITY INVENTORY:\n...",
  "token_count": 1450
}
```

**Response Fields:**
- `context` (string) - Formatted context string with all Tier 1 components
- `token_count` (integer) - Rough token estimate (word count)

**Context Sections:**
1. Entity Inventory Summary
2. Areas/Rooms List
3. Available Services Summary
4. Device Capability Patterns
5. Helpers & Scenes Summary

**Status Codes:**
- `200 OK` - Context retrieved successfully
- `503 Service Unavailable` - Service not ready
- `500 Internal Server Error` - Failed to build context

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/context
```

---

#### Get System Prompt

**GET** `/api/v1/system-prompt`

Retrieve the base system prompt defining the agent's role and behavior.

**Response:**
```json
{
  "system_prompt": "You are a knowledgeable and helpful Home Assistant automation assistant...",
  "token_count": 850
}
```

**Response Fields:**
- `system_prompt` (string) - Base system prompt without context
- `token_count` (integer) - Rough token estimate

**Status Codes:**
- `200 OK` - System prompt retrieved successfully
- `503 Service Unavailable` - Service not ready

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/system-prompt
```

---

#### Get Complete Prompt

**GET** `/api/v1/complete-prompt`

Retrieve the complete system prompt with Tier 1 context injected, ready for OpenAI API calls.

**Response:**
```json
{
  "complete_prompt": "You are a knowledgeable and helpful Home Assistant automation assistant...\n\n---\n\nHOME ASSISTANT CONTEXT:\n...",
  "token_count": 2300
}
```

**Response Fields:**
- `complete_prompt` (string) - Complete system prompt with context injected
- `token_count` (integer) - Rough token estimate

**Status Codes:**
- `200 OK` - Complete prompt retrieved successfully
- `503 Service Unavailable` - Service not ready
- `500 Internal Server Error` - Failed to build context

**Example:**
```bash
curl http://ha-ai-agent-service:8030/api/v1/complete-prompt
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `400 Bad Request` - Invalid request parameters
- `500 Internal Server Error` - Internal service error
- `503 Service Unavailable` - Service not ready or dependencies unavailable

---

### Tool Endpoints

#### Get Available Tools

**GET** `/api/v1/tools`

Get list of available tool schemas for OpenAI function calling.

**Response:**
```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "create_automation_from_prompt",
        "description": "...",
        "parameters": {...}
      }
    }
  ],
  "count": 1,
  "tool_names": ["create_automation_from_prompt"]
}
```

#### Execute Tool (Direct)

**POST** `/api/v1/tools/execute`

Execute a tool call directly (not in OpenAI format).

**Request Body:**
```json
{
  "tool_name": "create_automation_from_prompt",
  "arguments": {
    "user_prompt": "...",
    "automation_yaml": "...",
    "alias": "..."
  }
}
```

#### Execute Tool (OpenAI Format)

**POST** `/api/v1/tools/execute-openai`

Execute a tool call in OpenAI format.

**Request Body:**
```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "create_automation_from_prompt",
    "arguments": "{\"user_prompt\": \"...\", \"automation_yaml\": \"...\", \"alias\": \"...\"}"
  }
}
```

---

## Performance

- **Context Building (with cache)**: < 100ms
- **Context Building (first call)**: < 500ms
- **System Prompt Retrieval**: < 10ms
- **Complete Prompt Building**: < 100ms
- **Chat Response Time**: < 3 seconds (includes OpenAI API call + tool execution)
- **Token Budget**: 16,000 input tokens (with automatic history truncation)

---

## Caching

Context components are cached with TTL-based expiration:
- Entity summaries: 5 minutes
- Areas list: 10 minutes
- Services summary: 10 minutes
- Capability patterns: 15 minutes
- Helpers & scenes summary: 10 minutes

Cache is stored in SQLite database (`ha_ai_agent.db`).

---

## Dependencies

The service depends on:
- **Home Assistant REST API** - For areas, services, and entity states
- **Data API Service** (Port 8006) - For entity queries
- **Device Intelligence Service** (Port 8028) - For device capability patterns

If dependencies are unavailable, the service will return context with unavailable sections marked.

---

## Example Usage

### Python Client Example

```python
import httpx

async with httpx.AsyncClient() as client:
    # Send a chat message
    response = await client.post(
        "http://ha-ai-agent-service:8030/api/v1/chat",
        json={
            "message": "Turn on the kitchen lights when motion is detected"
        }
    )
    data = response.json()
    
    print(f"Response: {data['message']}")
    print(f"Conversation ID: {data['conversation_id']}")
    
    # Follow-up message in same conversation
    if data.get('tool_calls'):
        print(f"Tool calls made: {len(data['tool_calls'])}")
    
    # Continue conversation
    response2 = await client.post(
        "http://ha-ai-agent-service:8030/api/v1/chat",
        json={
            "message": "Actually, make it turn off after 5 minutes",
            "conversation_id": data['conversation_id']
        }
    )
```

### cURL Example

```bash
# Send a chat message
curl -X POST http://localhost:8030/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Turn on the kitchen lights when motion is detected"
  }'

# List conversations
curl http://localhost:8030/api/v1/conversations?limit=10

# Get specific conversation
curl http://localhost:8030/api/v1/conversations/conv-abc123

# Get context (debug endpoint)
curl http://localhost:8030/api/v1/context
```

---

## Version History

- **v1.0** (Epic AI-20) - Full conversational AI agent with chat endpoints, conversation management, and automation creation
- **v0.9** (Epic AI-19) - Initial release with Tier 1 context injection

