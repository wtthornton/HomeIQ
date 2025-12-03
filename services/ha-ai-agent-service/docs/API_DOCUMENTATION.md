# HA AI Agent Service API Documentation

**Version:** 1.0  
**Base URL:** `http://ha-ai-agent-service:8030`  
**Status:** ✅ Complete (Epic AI-19)

---

## Overview

The HA AI Agent Service provides REST API endpoints for retrieving context and system prompts for a conversational Home Assistant AI agent.

---

## Endpoints

### Health Check

**GET** `/health`

Check service health and readiness.

**Response:**
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is not ready

---

### Get Context

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

### Get System Prompt

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

### Get Complete Prompt

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

## Performance

- **Context Building (with cache)**: < 100ms
- **Context Building (first call)**: < 500ms
- **System Prompt Retrieval**: < 10ms
- **Complete Prompt Building**: < 100ms

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
    # Get complete prompt for OpenAI
    response = await client.get(
        "http://ha-ai-agent-service:8030/api/v1/complete-prompt"
    )
    data = response.json()
    
    complete_prompt = data["complete_prompt"]
    # Use complete_prompt as system message in OpenAI API call
```

### cURL Example

```bash
# Get context only
curl http://ha-ai-agent-service:8030/api/v1/context

# Get system prompt only
curl http://ha-ai-agent-service:8030/api/v1/system-prompt

# Get complete prompt (recommended for OpenAI)
curl http://ha-ai-agent-service:8030/api/v1/complete-prompt
```

---

## Version History

- **v1.0** (Epic AI-19) - Initial release with Tier 1 context injection

