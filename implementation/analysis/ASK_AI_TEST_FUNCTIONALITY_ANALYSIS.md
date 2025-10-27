# Ask AI Test Functionality - Analysis

**Date:** December 2024  
**Analysis Type:** Integration Test Design  
**Feature:** Test Button Functionality in `/ask-ai` Interface

---

## Executive Summary

The Test button in the Ask AI interface allows users to create and immediately execute a temporary automation in Home Assistant before committing to a permanent solution. This analysis documents what data gets passed through the call chain when the Test button is clicked.

---

## Two Statements in Automation Suggestion

Based on the image descriptions provided, the automation suggestion contains:

1. **Main Automation Description** (bold, with lightbulb icon):
   > "Every minute on the minute → Flash the living room lights in a warm white for 2 seconds, then switch to cool white for 2 seconds, repeating this for the duration."
   
   - This represents the actionable automation logic
   - Includes trigger: "Every minute on the minute"
   - Includes action sequence: warm white → cool white flash pattern
   - Tags: "automation", "New", "85% confident"

2. **Summary/Description** (regular text):
   > "Create a rhythmic flash sequence with the living room lights every minute, alternating between warm and cool white."
   
   - This is a human-readable summary of the automation
   - Explains the intent more concisely

---

## Call Tree

### Frontend Flow

```typescript
// File: services/ai-automation-ui/src/pages/AskAI.tsx
handleSuggestionAction(suggestionId, 'test') → line 144
  ↓
// Shows loading toast
toast.loading('⏳ Creating and running test automation...') → line 157
  ↓
// API call
api.testAskAISuggestion(queryId, suggestionId) → line 160
```

### API Call Structure

```typescript
// File: services/ai-automation-ui/src/services/api.ts
async testAskAISuggestion(queryId: string, suggestionId: string): Promise<any> {
  return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/suggestions/${suggestionId}/test`, {
    method: 'POST',
  });
}
```

**What Gets Passed:**
- `queryId`: The unique ID of the original query
- `suggestionId`: The unique ID of the specific suggestion being tested

**What is NOT passed directly (fetched from backend):**
- The suggestion object with its description, trigger, actions, confidence
- The original query text
- Device information
- Entity mappings

### Backend Flow

```python
# File: services/ai-automation-service/src/api/ask_ai_router.py
@router.post("/query/{query_id}/suggestions/{suggestion_id}/test")  → line 637
async def test_suggestion_from_query(
    query_id: str,
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ha_client: HomeAssistantClient = Depends(get_ha_client)
) → Dict[str, Any]:
```

**Processing Steps:**

1. **Retrieve Query from Database** (line 662)
   ```python
   query = await db.get(AskAIQueryModel, query_id)
   ```

2. **Find Specific Suggestion** (lines 667-674)
   ```python
   for s in query.suggestions:
       if s.get('suggestion_id') == suggestion_id:
           suggestion = s
           break
   ```
   The suggestion object contains:
   - `suggestion_id`: Unique identifier
   - `description`: Human-readable description
   - `trigger_summary`: What triggers the automation
   - `action_summary`: What the automation does
   - `devices_involved`: Array of device/entity information
   - `confidence`: Confidence score (e.g., 0.85)

3. **Generate YAML** (line 681)
   ```python
   automation_yaml = await generate_automation_yaml(suggestion, query.original_query)
   ```
   
   This creates Home Assistant automation YAML like:
   ```yaml
   id: office_lights_test_abc123
   alias: "[TEST] Turn on Office Lights"
   trigger:
     - platform: state
       entity_id: binary_sensor.front_door
       to: 'on'
   action:
     - service: light.flash
       entity_id: light.office
       data:
         color_name: warm_white
         duration: 2
   ```

4. **Validate YAML** (line 689)
   ```python
   validation_result = await ha_client.validate_automation(automation_yaml)
   ```

5. **Modify for Test** (lines 706-714)
   ```python
   # Add "test_" prefix to ID
   test_id = f"test_{original_id}_{suggestion_id.split('-')[-1]}"
   automation_data['id'] = test_id
   automation_data['alias'] = f"[TEST] {automation_data.get('alias', 'AI Test Automation')}"
   ```

6. **Create Automation in HA** (line 718)
   ```python
   creation_result = await ha_client.create_automation(test_automation_yaml)
   ```

7. **Trigger Immediately** (line 736)
   ```python
   trigger_success = await ha_client.trigger_automation(automation_id)
   ```

8. **Disable Automation** (line 739)
   ```python
   await ha_client.disable_automation(automation_id)
   ```

### Home Assistant Client Flow

```python
# File: services/ai-automation-service/src/clients/ha_client.py

# Step 1: Create automation
async def create_automation(automation_yaml: str) → line 645
  ↓
  POST {ha_url}/api/config/automation/config/{automation_id}
  ↓
  Enable the automation → line 692

# Step 2: Trigger automation
async def trigger_automation(automation_id: str) → line 453
  ↓
  POST {ha_url}/api/services/automation/trigger
  json: {"entity_id": automation_id}
  ↓
  Automation runs immediately

# Step 3: Disable automation
async def disable_automation(automation_id: str) → line 425
  ↓
  POST {ha_url}/api/services/automation/turn_off
  json: {"entity_id": automation_id}
  ↓
  Automation stays in HA but disabled
```

---

## Complete Data Flow Summary

### What Gets Passed (Explicit Payload)

```json
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
```

**Request:**
- No request body (empty POST)
- Only path parameters: `query_id` and `suggestion_id`

**Response:**
```json
{
  "suggestion_id": "suggestion-123",
  "query_id": "query-abc",
  "valid": true,
  "executed": true,
  "automation_id": "automation.test_office_lights_flash_abc123",
  "automation_yaml": "...",
  "test_automation_yaml": "...",
  "validation_details": {
    "error": null,
    "warnings": [],
    "entity_count": 2
  },
  "message": "✅ Test automation executed successfully! ..."
}
```

### What Gets Retrieved (Implicitly Fetched)

From Database (AskAIQueryModel):
```json
{
  "query_id": "query-abc",
  "original_query": "I want to flash the living room lights every min",
  "suggestions": [
    {
      "suggestion_id": "suggestion-123",
      "description": "Flash the living room lights...",
      "trigger_summary": "Every minute on the minute",
      "action_summary": "Flash living room lights...",
      "devices_involved": [
        {
          "entity_id": "light.living_room",
          "domain": "light",
          "area": "Living Room"
        }
      ],
      "confidence": 0.85
    }
  ]
}
```

### Generated Automation YAML

```yaml
id: test_ai_flash_living_room_abc123
alias: "[TEST] Flash Living Room Lights"
description: "Create a rhythmic flash sequence with the living room lights every minute, alternating between warm and cool white"
trigger:
  - platform: time_pattern
    minutes: "/1"
    seconds: 0
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      color_name: warm_white
      brightness_pct: 100
  - delay: "00:00:02"
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      color_name: cool_white
      brightness_pct: 100
  - delay: "00:00:02"
mode: single
```

### Home Assistant API Calls

1. **Create Automation:**
   ```
   POST http://192.168.1.86:8123/api/config/automation/config/test_ai_flash_living_room_abc123
   Authorization: Bearer {token}
   Content-Type: application/json
   
   {
     "id": "test_ai_flash_living_room_abc123",
     "alias": "[TEST] Flash Living Room Lights",
     ...
   }
   ```

2. **Trigger Automation:**
   ```
   POST http://192.168.1.86:8123/api/services/automation/trigger
   Authorization: Bearer {token}
   Content-Type: application/json
   
   {
     "entity_id": "automation.test_ai_flash_living_room_abc123"
   }
   ```

3. **Disable Automation:**
   ```
   POST http://192.168.1.86:8123/api/services/automation/turn_off
   Authorization: Bearer {token}
   Content-Type: application/json
   
   {
     "entity_id": "automation.test_ai_flash_living_room_abc123"
   }
   ```

---

## Integration Test Requirements

To create a repeatable integration test for this functionality, we need to:

1. **Mock Home Assistant API:**
   - Accept POST to `/api/config/automation/config/{id}`
   - Accept POST to `/api/services/automation/trigger`
   - Accept POST to `/api/services/automation/turn_off`
   - Return appropriate success responses

2. **Verify:**
   - Automation YAML is generated correctly
   - Automation ID has `test_` prefix and `[TEST]` in alias
   - Automation is created in HA (mock)
   - Automation is triggered
   - Automation is disabled after triggering
   - Success toast appears in UI

3. **Test Edge Cases:**
   - Invalid automation YAML
   - Entity does not exist
   - HA connection failure
   - Trigger fails but automation was created

---

## References

- Frontend: `services/ai-automation-ui/src/pages/AskAI.tsx`
- Frontend API: `services/ai-automation-ui/src/services/api.ts`
- Backend Router: `services/ai-automation-service/src/api/ask_ai_router.py`
- HA Client: `services/ai-automation-service/src/clients/ha_client.py`
- Existing E2E Tests: `tests/e2e/ask-ai-complete.spec.ts`
- Page Object: `tests/e2e/page-objects/AskAIPage.ts`

