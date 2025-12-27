# v1 to v2 Migration Guide

**Last Updated:** January 2025  
**Status:** Production Ready

## Overview

This guide helps you migrate from the v1 Ask AI API to the new v2 Conversation API. The v2 API provides:

- **Conversation-centric design** - Track multi-turn conversations with persistent IDs
- **Explicit response types** - Clear distinction between automation generation, actions, and information
- **Streaming support** - Real-time response streaming for better UX
- **Function calling** - Direct execution of Home Assistant services
- **Enhanced confidence scoring** - Multi-factor confidence breakdown
- **Better error recovery** - Actionable error messages and suggestions

## Migration Timeline

### Phase 1: Preparation (Week 1)
- Review this guide
- Export legacy data
- Test v2 API in development

### Phase 2: Migration (Week 2)
- Run database migration
- Update API clients
- Test critical flows

### Phase 3: Deployment (Week 3)
- Deploy v2 API
- Monitor for issues
- Gradual rollout

## Breaking Changes

### API Endpoints

| v1 Endpoint | v2 Endpoint | Notes |
|------------|-------------|-------|
| `POST /api/v1/ask-ai/query` | `POST /api/v2/conversations` | Returns conversation ID |
| `POST /api/v1/ask-ai/query/{id}/refine` | `POST /api/v2/conversations/{id}/message` | Use message endpoint |
| `GET /api/v1/ask-ai/query/{id}/suggestions` | `GET /api/v2/conversations/{id}/suggestions` | Same functionality |
| `POST /api/v1/ask-ai/clarify` | `POST /api/v2/conversations/{id}/message` | Integrated into message flow |

### Response Format

**v1 Response:**
```json
{
  "query_id": "query-abc123",
  "original_query": "turn on office lights",
  "suggestions": [...],
  "confidence": 0.85,
  "clarification_needed": false
}
```

**v2 Response:**
```json
{
  "conversation_id": "conv-abc123",
  "turn_number": 1,
  "response_type": "automation_generated",
  "content": "I found 2 automation suggestions...",
  "suggestions": [...],
  "confidence": {
    "overall": 0.85,
    "factors": {...},
    "explanation": "..."
  }
}
```

### Database Schema

**New Tables:**
- `conversations` - Conversation metadata
- `conversation_turns` - Individual messages/turns
- `confidence_factors` - Detailed confidence breakdown
- `function_calls` - Function execution tracking
- `automation_suggestions_v2` - Enhanced suggestion storage

**Legacy Tables (Preserved):**
- `ask_ai_queries` - Still accessible for historical data
- `clarification_sessions` - Still accessible for historical data
- `suggestions` - Still accessible for historical data

## Migration Steps

### Step 1: Export Legacy Data

```bash
cd services/ai-automation-service
python scripts/export_legacy_data.py --output data/legacy_export.json
```

This exports:
- All `AskAIQuery` records
- All `ClarificationSessionDB` records
- All related suggestions

### Step 2: Run Database Migration

```bash
python scripts/run_v2_migration.py
```

This creates:
- New v2 tables
- Indexes for performance
- Foreign key constraints

**Note:** This is non-destructive - old tables are preserved.

### Step 3: Import Legacy Data (Optional)

If you want to migrate historical data:

```bash
python scripts/import_to_v2.py --input data/legacy_export.json
```

This converts:
- `AskAIQuery` → `Conversation` + `ConversationTurn`
- `ClarificationSessionDB` → `ConversationTurn` with clarification questions
- Suggestions → `AutomationSuggestionV2`

### Step 4: Update API Clients

#### Python Example

**v1 Code:**
```python
response = await client.post("/api/v1/ask-ai/query", json={
    "query": "turn on office lights",
    "user_id": "user123"
})
query_id = response.json()["query_id"]
```

**v2 Code:**
```python
response = await client.post("/api/v2/conversations", json={
    "query": "turn on office lights",
    "user_id": "user123"
})
conversation_id = response.json()["conversation_id"]

# Send follow-up message
turn_response = await client.post(
    f"/api/v2/conversations/{conversation_id}/message",
    json={"message": "make it blue"}
)
```

#### TypeScript Example

**v1 Code:**
```typescript
const response = await api.askAIQuery("turn on office lights", {
  userId: "user123"
});
const queryId = response.query_id;
```

**v2 Code:**
```typescript
import apiV2 from './services/api-v2';

const conversation = await apiV2.startConversation({
  query: "turn on office lights",
  user_id: "user123"
});

const turnResponse = await apiV2.sendMessage(
  conversation.conversation_id,
  { message: "make it blue" }
);
```

### Step 5: Update Frontend Components

**Enable v2 API:**
```typescript
// Set environment variable
VITE_USE_V2_API=true

// Or in localStorage
localStorage.setItem('use-v2-api', 'true');
```

**Use v2 Hook:**
```typescript
import { useConversationV2 } from '../hooks/useConversationV2';

const {
  conversation,
  turns,
  startConversation,
  sendMessage,
} = useConversationV2({ userId: 'user123' });
```

## Response Type Handling

v2 API uses explicit response types:

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

**Handle each type:**
```typescript
switch (turnResponse.response_type) {
  case ResponseType.AUTOMATION_GENERATED:
    // Show suggestions
    break;
  case ResponseType.CLARIFICATION_NEEDED:
    // Show clarification dialog
    break;
  case ResponseType.ACTION_DONE:
    // Show success message
    break;
  // ...
}
```

## Streaming Support

v2 API supports Server-Sent Events (SSE) for streaming:

```typescript
await apiV2.streamConversationTurn(
  conversationId,
  message,
  (chunk) => {
    // Update UI with partial response
    setPartialResponse(chunk);
  },
  (error) => {
    // Handle error
  }
);
```

## Function Calling

v2 API supports direct function execution:

```typescript
// Execute immediate action
const result = await apiV2.executeAction({
  query: "turn on office lights",
  user_id: "user123"
});

if (result.success) {
  console.log(`Action executed: ${result.action_type}`);
}
```

## Error Handling

v2 API provides structured error responses:

```typescript
try {
  const response = await apiV2.sendMessage(conversationId, { message });
} catch (error) {
  if (error instanceof APIError) {
    // Handle specific error
    if (error.status === 404) {
      // Conversation not found
    } else if (error.status === 422) {
      // Validation error
    }
  }
}
```

## Rollback Plan

If you need to rollback:

1. **Disable v2 API:**
   ```bash
   # Remove v2 router registration in main.py
   # Or set feature flag
   ```

2. **Use v1 endpoints:**
   - v1 endpoints remain functional
   - No data loss (v2 tables are separate)

3. **Database rollback:**
   ```sql
   -- v2 tables can be dropped if needed
   DROP TABLE IF EXISTS conversations;
   DROP TABLE IF EXISTS conversation_turns;
   -- etc.
   ```

## Testing Checklist

- [ ] Export legacy data
- [ ] Run database migration
- [ ] Test conversation creation
- [ ] Test message sending
- [ ] Test suggestion retrieval
- [ ] Test clarification flow
- [ ] Test action execution
- [ ] Test error handling
- [ ] Test streaming (if enabled)
- [ ] Verify data integrity
- [ ] Performance testing

## Support

For issues or questions:
- Check API documentation: `docs/api/v2/conversation-api.md`
- Review architecture docs: `docs/architecture/conversation-system-v2.md`
- Open an issue on GitHub

## FAQ

**Q: Can I use both v1 and v2 APIs simultaneously?**  
A: Yes, both APIs are available. v1 endpoints remain functional.

**Q: Will my existing data be migrated automatically?**  
A: No, migration is optional. Use the export/import scripts if you want to migrate historical data.

**Q: What happens to existing suggestions?**  
A: Existing suggestions remain in the `suggestions` table. New suggestions go to `automation_suggestions_v2`.

**Q: Can I rollback after migration?**  
A: Yes, v1 endpoints remain functional. v2 tables can be dropped if needed.

**Q: How do I enable streaming?**  
A: Use the `/api/v2/conversations/{id}/stream` endpoint or enable streaming in the `useConversationV2` hook.

