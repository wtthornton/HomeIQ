# v2 Conversation API Documentation

**Last Updated:** January 2025  
**Base URL:** `/api/v2`

## Overview

The v2 Conversation API provides a modern, conversation-centric interface for AI-powered automation authoring. It supports:

- Multi-turn conversations with persistent IDs
- Explicit response types (automation, action, information, clarification)
- Streaming responses for real-time updates
- Function calling for immediate actions
- Enhanced confidence scoring
- Better error recovery

## Authentication

All endpoints require authentication:

```http
Authorization: Bearer {api_key}
X-HomeIQ-API-Key: {api_key}
```

## Endpoints

### Conversations

#### Start Conversation

Start a new conversation with an initial query.

```http
POST /api/v2/conversations
```

**Request:**
```json
{
  "query": "turn on office lights when I get home",
  "user_id": "user123",
  "conversation_type": "automation",  // optional
  "context": {}  // optional
}
```

**Response (201 Created):**
```json
{
  "conversation_id": "conv-abc123",
  "user_id": "user123",
  "conversation_type": "automation",
  "status": "active",
  "initial_query": "turn on office lights when I get home",
  "created_at": "2025-01-20T10:00:00Z"
}
```

#### Send Message

Send a message in an existing conversation.

```http
POST /api/v2/conversations/{conversation_id}/message
```

**Request:**
```json
{
  "message": "make it blue instead",
  "context": {}  // optional
}
```

**Response (200 OK):**
```json
{
  "conversation_id": "conv-abc123",
  "turn_number": 2,
  "response_type": "automation_generated",
  "content": "I've updated the automation to use blue lights...",
  "suggestions": [
    {
      "suggestion_id": "sugg-xyz789",
      "title": "Office Lights - Blue",
      "description": "Turn on office lights (blue) when user arrives home",
      "automation_yaml": "...",
      "confidence": 0.92,
      "validated_entities": {
        "office lights": "light.office_main"
      },
      "status": "draft"
    }
  ],
  "confidence": {
    "overall": 0.92,
    "factors": {
      "entity_resolution": 0.95,
      "intent_clarity": 0.90,
      "context_relevance": 0.91
    },
    "explanation": "High confidence due to clear entities and intent"
  },
  "processing_time_ms": 1250,
  "next_actions": [
    "Review the automation YAML",
    "Test the automation",
    "Deploy to Home Assistant"
  ],
  "created_at": "2025-01-20T10:01:00Z"
}
```

#### Get Conversation

Retrieve full conversation history.

```http
GET /api/v2/conversations/{conversation_id}
```

**Response (200 OK):**
```json
{
  "conversation_id": "conv-abc123",
  "user_id": "user123",
  "conversation_type": "automation",
  "status": "active",
  "initial_query": "turn on office lights when I get home",
  "turns": [
    {
      "conversation_id": "conv-abc123",
      "turn_number": 1,
      "response_type": "automation_generated",
      "content": "...",
      "suggestions": [...],
      "created_at": "2025-01-20T10:00:00Z"
    },
    {
      "conversation_id": "conv-abc123",
      "turn_number": 2,
      "response_type": "automation_generated",
      "content": "...",
      "suggestions": [...],
      "created_at": "2025-01-20T10:01:00Z"
    }
  ],
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:01:00Z",
  "completed_at": null
}
```

#### Get Suggestions

Get all suggestions for a conversation.

```http
GET /api/v2/conversations/{conversation_id}/suggestions
```

**Response (200 OK):**
```json
{
  "suggestions": [
    {
      "suggestion_id": "sugg-xyz789",
      "title": "Office Lights Automation",
      "description": "...",
      "automation_yaml": "...",
      "confidence": 0.92,
      "validated_entities": {...},
      "status": "draft"
    }
  ]
}
```

#### Stream Conversation Turn

Stream conversation turn with Server-Sent Events.

```http
POST /api/v2/conversations/{conversation_id}/stream
```

**Request:**
```json
{
  "message": "turn on office lights"
}
```

**Response (200 OK, text/event-stream):**
```
data: {"turn_number": 1, "content": "Processing your request..."}
data: {"turn_number": 1, "content": "Found 2 devices matching 'office lights'..."}
data: {"turn_number": 1, "response_type": "automation_generated", "suggestions": [...]}
```

### Actions

#### Execute Immediate Action

Execute an immediate action (e.g., "turn on office lights").

```http
POST /api/v2/actions/execute
```

**Request:**
```json
{
  "query": "turn on office lights",
  "user_id": "user123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "action_type": "turn_on_light",
  "entity_id": "light.office_main",
  "result": {
    "state": "on",
    "brightness": 255
  },
  "message": "Successfully turned on office lights",
  "execution_time_ms": 150
}
```

### Automations

#### Generate Automation

Generate automation YAML from a suggestion.

```http
POST /api/v2/automations/generate
```

**Request:**
```json
{
  "suggestion_id": "sugg-xyz789",
  "conversation_id": "conv-abc123",
  "turn_id": 1
}
```

**Response (200 OK):**
```json
{
  "suggestion_id": "sugg-xyz789",
  "automation_yaml": "alias: Office Lights Automation\n...",
  "validation_result": {
    "syntax_valid": true,
    "structure_valid": true,
    "entities_valid": true,
    "safety_score": 0.95
  },
  "confidence": 0.92
}
```

#### Test Automation

Test an automation before deployment.

```http
POST /api/v2/automations/test
```

**Request:**
```json
{
  "suggestion_id": "sugg-xyz789",
  "automation_yaml": "..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "state_changes": {
    "light.office_main": {
      "before": "off",
      "after": "on"
    }
  },
  "errors": [],
  "warnings": [],
  "execution_time_ms": 200
}
```

#### Deploy Automation

Deploy an automation to Home Assistant.

```http
POST /api/v2/automations/deploy
```

**Request:**
```json
{
  "suggestion_id": "sugg-xyz789",
  "automation_yaml": "...",
  "automation_id": "automation.office_lights"  // optional
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "automation_id": "automation.office_lights",
  "message": "Automation deployed successfully",
  "deployed_at": "2025-01-20T10:05:00Z"
}
```

#### List Automations

List all automations for a conversation (or all automations).

```http
GET /api/v2/automations?conversation_id={conversation_id}
```

**Response (200 OK):**
```json
{
  "automations": [
    {
      "suggestion_id": "sugg-xyz789",
      "conversation_id": "conv-abc123",
      "title": "Office Lights Automation",
      "description": "...",
      "status": "deployed",
      "confidence": 0.92,
      "created_at": "2025-01-20T10:00:00Z",
      "updated_at": "2025-01-20T10:05:00Z"
    }
  ]
}
```

## Response Types

### ResponseType Enum

```typescript
enum ResponseType {
  AUTOMATION_GENERATED = "automation_generated",
  CLARIFICATION_NEEDED = "clarification_needed",
  ACTION_DONE = "action_done",
  INFORMATION_PROVIDED = "information_provided",
  ERROR = "error",
  NO_INTENT_MATCH = "no_intent_match",
}
```

### Handling Each Type

**AUTOMATION_GENERATED:**
- Contains `suggestions` array
- User should review and approve/reject suggestions

**CLARIFICATION_NEEDED:**
- Contains `clarification_questions` array
- User should answer questions to improve confidence

**ACTION_DONE:**
- Action was executed immediately
- Contains `result` with execution details

**INFORMATION_PROVIDED:**
- Informational response (no action taken)
- Contains `content` with information

**ERROR:**
- Error occurred during processing
- Contains `content` with error message
- May contain `next_actions` with recovery suggestions

**NO_INTENT_MATCH:**
- Could not determine user intent
- Contains `content` with explanation
- May contain `next_actions` with suggestions

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request: message cannot be empty"
}
```

### 404 Not Found
```json
{
  "detail": "Conversation not found: conv-abc123"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error. Please try again later."
}
```

## Rate Limiting

- **Conversation creation:** 10 requests/minute per user
- **Message sending:** 30 requests/minute per conversation
- **Action execution:** 60 requests/minute per user

Rate limit headers:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1642680000
```

## Examples

### Complete Flow

```typescript
// 1. Start conversation
const conversation = await apiV2.startConversation({
  query: "turn on office lights when I get home",
  user_id: "user123"
});

// 2. Get initial response (from start_conversation)
const initialTurn = await apiV2.getConversation(conversation.conversation_id);
console.log(initialTurn.turns[0].suggestions);

// 3. Refine automation
const refinedTurn = await apiV2.sendMessage(
  conversation.conversation_id,
  { message: "make it blue instead" }
);

// 4. Generate automation YAML
const automation = await apiV2.generateAutomation({
  suggestion_id: refinedTurn.suggestions[0].suggestion_id,
  conversation_id: conversation.conversation_id,
  turn_id: refinedTurn.turn_number
});

// 5. Test automation
const testResult = await apiV2.testAutomation({
  suggestion_id: automation.suggestion_id,
  automation_yaml: automation.automation_yaml
});

// 6. Deploy automation
if (testResult.success) {
  const deployResult = await apiV2.deployAutomation({
    suggestion_id: automation.suggestion_id,
    automation_yaml: automation.automation_yaml
  });
  console.log(`Deployed: ${deployResult.automation_id}`);
}
```

### Streaming Example

```typescript
await apiV2.streamConversationTurn(
  conversationId,
  "turn on office lights",
  (chunk) => {
    // Update UI with partial response
    setPartialContent(chunk.content);
    if (chunk.suggestions) {
      setSuggestions(chunk.suggestions);
    }
  },
  (error) => {
    console.error("Streaming error:", error);
  }
);
```

## SDKs

### TypeScript/JavaScript

```bash
npm install @homeiq/api-v2
```

```typescript
import { ConversationClient } from '@homeiq/api-v2';

const client = new ConversationClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.homeiq.local'
});
```

### Python

```bash
pip install homeiq-api-v2
```

```python
from homeiq_api_v2 import ConversationClient

client = ConversationClient(
    api_key="your-api-key",
    base_url="https://api.homeiq.local"
)
```

## Support

- **Documentation:** `docs/api/v2/`
- **Migration Guide:** `docs/migration/v1-to-v2-migration-guide.md`
- **Architecture:** `docs/architecture/conversation-system-v2.md`
- **GitHub Issues:** [Create an issue](https://github.com/your-repo/issues)

