# HA Conversation v2 - Quick Start Guide

## Overview

The v2 conversation system provides a modular, maintainable architecture for natural language automation creation. This guide shows how to use the new system.

## Key Concepts

### ServiceContainer
Centralized dependency injection - all services accessed via container:
```python
from ...services.service_container import get_service_container

container = get_service_container()
entities = await container.entity_extractor.extract(query)
```

### Conversation Flow
1. Start conversation → Get `conversation_id`
2. Send messages → Get responses with `response_type`
3. Handle responses → Suggestions, clarification, or actions
4. Generate automation → Test → Deploy

## API Usage Examples

### Start a Conversation

```bash
POST /api/v2/conversations
{
  "query": "turn on office lights when I sit at my desk",
  "user_id": "user123"
}

Response:
{
  "conversation_id": "conv-abc123",
  "user_id": "user123",
  "conversation_type": "automation",
  "status": "active",
  "initial_query": "...",
  "created_at": "2025-01-XX..."
}
```

### Send a Message

```bash
POST /api/v2/conversations/{conversation_id}/message
{
  "message": "make it blue instead"
}

Response:
{
  "conversation_id": "conv-abc123",
  "turn_number": 2,
  "response_type": "automation_generated",
  "content": "...",
  "suggestions": [...],
  "confidence": {...},
  "next_actions": [...]
}
```

### Execute Immediate Action

```bash
POST /api/v2/actions/execute
{
  "query": "turn on office lights",
  "user_id": "user123"
}

Response:
{
  "success": true,
  "action_type": "turn_on_light",
  "entity_id": "light.office",
  "result": {"action": "turned_on"},
  "message": "Action executed: turn_on_light"
}
```

## Response Types

- `automation_generated` - Automation suggestions ready
- `clarification_needed` - Need more information
- `action_done` - Immediate action completed
- `information_provided` - Information query answered
- `error` - Error occurred
- `no_intent_match` - Couldn't understand query

## Service Usage

### Entity Extraction
```python
container = get_service_container()
entities = await container.entity_extractor.extract("turn on office lights")
```

### Entity Validation
```python
validation_results = await container.entity_validator.validate_entities(
    entity_ids=["light.office"],
    query_context="office lights"
)
```

### YAML Generation
```python
yaml = await container.yaml_generator.generate(
    suggestion=suggestion_dict,
    original_query="turn on office lights",
    validated_entities={"office lights": "light.office"}
)
```

### Confidence Calculation
```python
confidence = await container.confidence_calculator.calculate_confidence(
    query="turn on office lights",
    entities=entities,
    ambiguities=[],
    validation_result={}
)
```

## Database Schema

### Conversations Table
```sql
SELECT * FROM conversations WHERE user_id = 'user123';
```

### Conversation Turns
```sql
SELECT * FROM conversation_turns 
WHERE conversation_id = 'conv-abc123' 
ORDER BY turn_number;
```

### Automation Suggestions
```sql
SELECT * FROM automation_suggestions 
WHERE conversation_id = 'conv-abc123';
```

## Migration Workflow

1. **Export legacy data:**
   ```bash
   python scripts/export_legacy_data.py
   ```

2. **Run v2 migration:**
   ```bash
   python scripts/run_v2_migration.py
   ```

3. **Import legacy data:**
   ```bash
   python scripts/import_to_v2.py --input data/legacy_export.json
   ```

## Error Handling

All errors return structured responses with recovery actions:
```python
error_response = await container.error_recovery.handle_processing_error(
    error=exception,
    query="turn on lights",
    partial_results={}
)
```

## Next Steps

1. Test v2 API endpoints
2. Update frontend to use v2 client
3. Run integration tests
4. Monitor performance
5. Complete remaining phases (6-10)

