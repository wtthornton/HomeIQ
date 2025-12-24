# Specific Automation E2E Test

## Overview

This test directly calls the Test API endpoint with a **known** query_id and suggestion_id from the database to verify the complete Test button workflow without creating new data.

## Test Data

- **Query ID:** `query-649c39bb`
- **Query Text:** "Flash the office lights every min"
- **Suggestion ID:** `ask-ai-8bdbe1b5`
- **Description:** "Create a lively office ambiance by cycling through RGB colors on the office lights every minute to mimic a disco effect, enhancing your focus while working."

## What It Tests

1. **Database Retrieval:** Fetches query and suggestion from database
2. **AI Simplification:** Uses OpenAI to simplify the command (removes time constraints)
3. **HA Execution:** Executes the simplified command via HA Conversation API
4. **Response Validation:** Verifies execution status and response structure

## API Endpoint Tested

```
POST /api/v1/ask-ai/query/query-649c39bb/suggestions/ask-ai-8bdbe1b5/test
```

## Expected Flow

```
User clicks Test button
  ↓
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
  ↓
Backend fetches query from database (query-649c39bb)
  ↓
Backend finds suggestion in query.suggestions array
  ↓
Backend simplifies command: "Cycle office lights through RGB colors"
  ↓
Backend executes via HA: POST /api/conversation/process
  ↓
Backend returns: {executed: true/false, command: "...", response: "..."}
  ↓
Frontend shows success/error toast
```

## Running the Test

### Option 1: Run directly
```bash
cd tests/integration
python test_ask_ai_specific_automation.py
```

### Option 2: Run with pytest
```bash
pytest tests/integration/test_ask_ai_specific_automation.py -v
```

### Option 3: Run from project root
```bash
python -m pytest tests/integration/test_ask_ai_specific_automation.py -v
```

## Test Configuration

- **Base URL:** `http://localhost:8024` (Docker mapped from 8018)
- **API Path:** `/api/v1/ask-ai`
- **Timeout:** 120 seconds (allows time for OpenAI + HA execution)

## Expected Output

```
================================================================================
E2E TEST: Known Automation Test
================================================================================
Query ID: query-649c39bb
Suggestion ID: ask-ai-8bdbe1b5

🧪 Step 1: Calling Test API endpoint...
Response Status: 200

Response Data:
{
  "suggestion_id": "ask-ai-8bdbe1b5",
  "query_id": "query-649c39bb",
  "executed": true,
  "command": "Cycle office lights through RGB colors",
  "original_description": "Create a lively office ambiance by cycling through RGB colors...",
  "response": "Office lights updated successfully",
  "message": "✅ Quick test successful! Command 'Cycle office lights through RGB colors' was executed."
}

✅ All required fields present
✅ All values match expected
✅ Command was simplified (shorter than original)
✅ Time constraints removed from command
✅ Automation executed successfully via HA Conversation API
```

## What Makes This Test Different

1. **Uses Real Database Data:** Tests with actual query/suggestion from database
2. **No Query Creation:** Skips the "create query" step, goes straight to testing
3. **Known Automation:** Tests a specific, known automation that exists
4. **Full E2E:** Tests complete flow from API call to HA execution
5. **Verifiable:** Can check the exact automation in the UI after test

## Troubleshooting

### Test fails with "query not found"
- Make sure `query-649c39bb` exists in database
- Check that ai-automation-service is running

### Test fails with "connection refused"
- Verify Docker container is running: `docker ps | grep ai-automation-service`
- Check port mapping: `8024:8018`

### Test fails with "executed: false"
- Check HA connection
- Verify entity exists: "office lights"
- Check HA logs for errors

## Next Steps

To use a different query/suggestion:
1. Find a query in the database
2. Extract query_id and suggestion_id
3. Update the constants in the test file
4. Run the test

