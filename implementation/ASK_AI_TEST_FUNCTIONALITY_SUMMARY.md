# Ask AI Test Functionality - Summary

**Date:** December 2024  
**Feature:** Test Button in `/ask-ai` Interface  
**Status:** ✅ Complete Analysis and Integration Test Created

---

## Summary

I've researched the Test functionality in the `/ask-ai` interface and created a comprehensive, repeatable integration test. Here's what was accomplished:

### What Was Researched

1. **The Two Statements in the Automation Suggestion:**
   - **Statement 1 (Main Automation):** "Every minute on the minute → Flash the living room lights in a warm white for 2 seconds, then switch to cool white for 2 seconds, repeating this for the duration."
     - Includes trigger, action sequence, and technical details
     - Displayed with lightbulb icon
     - Tags: "automation", "New", "85% confident"
   
   - **Statement 2 (Summary):** "Create a rhythmic flash sequence with the living room lights every minute, alternating between warm and cool white."
     - Human-readable summary/description
     - Explains the intent more concisely

2. **What Gets Passed When Test Button is Clicked:**
   - **Frontend Request:**
     ```typescript
     POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
     ```
     - Empty POST body
     - Only path parameters: `query_id` and `suggestion_id`
   
   - **What Gets Retrieved by Backend:**
     - Query object from database (including `original_query`)
     - Specific suggestion object from query.suggestions array
     - Suggestion contains: description, trigger_summary, action_summary, devices_involved, confidence

3. **Complete Call Tree:**
   ```
   User clicks Test button
     ↓
   Frontend: AskAI.tsx line 144 → handleSuggestionAction('test')
     ↓
   API call: POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
     ↓
   Backend: ask_ai_router.py line 637 → test_suggestion_from_query()
     ├─ Fetch query from database (line 662)
     ├─ Find suggestion (line 667-674)
     ├─ Generate YAML (line 681)
     ├─ Validate YAML (line 689)
     ├─ Add [TEST] prefix to automation (line 706-714)
     ├─ Create in HA (line 718)
     ├─ Trigger immediately (line 736)
     └─ Disable automation (line 739)
     ↓
   HA Client: ha_client.py
     ├─ create_automation() → POST /api/config/automation/config/{id}
     ├─ trigger_automation() → POST /api/services/automation/trigger
     └─ disable_automation() → POST /api/services/automation/turn_off
     ↓
   Response with execution status
     ↓
   Frontend shows success toast
   ```

### Documents Created

1. **Analysis Document:**
   - `implementation/analysis/ASK_AI_TEST_FUNCTIONALITY_ANALYSIS.md`
   - Complete technical analysis of the Test functionality
   - Documents data flow, API calls, and HA interactions
   - Includes YAML examples and response structures

2. **Integration Test:**
   - `tests/integration/ask-ai-test-button.spec.ts`
   - Repeatable integration test suite
   - Tests:
     - Happy path (successful test execution)
     - Call tree verification (API request structure)
     - Data flow verification (suggestion data, automation IDs)
     - Edge cases (validation failures, missing entities)

### Key Findings

**Test Button Workflow:**
1. User submits query → Gets suggestions
2. User clicks Test → Sends only `query_id` and `suggestion_id`
3. Backend retrieves full suggestion data from database
4. Backend generates YAML
5. Backend creates automation with `[TEST]` prefix in alias
6. Backend triggers automation immediately
7. Backend disables automation (prevents re-triggering)
8. Frontend shows success toast with automation ID

**Data Structure:**
```typescript
// Request (minimal)
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test

// Response (comprehensive)
{
  suggestion_id: string,
  query_id: string,
  valid: boolean,
  executed: boolean,
  automation_id: string,  // e.g., "automation.test_office_lights_abc123"
  automation_yaml: string,
  test_automation_yaml: string,
  validation_details: {
    error: string | null,
    warnings: string[],
    entity_count: number
  },
  message: string
}
```

**Generated Automation Format:**
```yaml
id: test_office_lights_abc123
alias: "[TEST] Turn on Office Lights"
description: "..."
trigger:
  - platform: state
    entity_id: sensor.some_trigger
action:
  - service: light.turn_on
    target:
      entity_id: light.office
mode: single
```

### Integration Test Features

The created test suite (`ask-ai-test-button.spec.ts`) includes:

1. **Happy Path Test:**
   - Submits query
   - Clicks Test button
   - Verifies automation created, triggered, and disabled
   - Checks automation ID format
   - Verifies success toast

2. **API Verification Test:**
   - Monitors network requests
   - Verifies POST method and URL structure
   - Extracts query_id and suggestion_id from URL
   - Confirms empty request body

3. **Backend Response Verification:**
   - Captures API response
   - Verifies response structure
   - Checks all required fields present
   - Logs automation details

4. **Data Flow Test:**
   - Verifies suggestion descriptions
   - Checks card text structure
   - Ensures unique automation IDs
   - Tests multiple sequential test runs

### How to Run the Test

```bash
# Run the integration test
npx playwright test tests/integration/ask-ai-test-button.spec.ts

# Run with UI (debug mode)
npx playwright test tests/integration/ask-ai-test-button.spec.ts --headed

# Run specific test
npx playwright test tests/integration/ask-ai-test-button.spec.ts -g "Test button creates"
```

### References

- **Frontend:** `services/ai-automation-ui/src/pages/AskAI.tsx`
- **API Service:** `services/ai-automation-ui/src/services/api.ts`
- **Backend Router:** `services/ai-automation-service/src/api/ask_ai_router.py`
- **HA Client:** `services/ai-automation-service/src/clients/ha_client.py`
- **Analysis:** `implementation/analysis/ASK_AI_TEST_FUNCTIONALITY_ANALYSIS.md`
- **Test:** `tests/integration/ask-ai-test-button.spec.ts`

---

## Conclusion

The Test button functionality creates a temporary automation in Home Assistant, triggers it immediately, then disables it. The integration test verifies this complete flow from UI click through HA execution, ensuring the feature works reliably.

