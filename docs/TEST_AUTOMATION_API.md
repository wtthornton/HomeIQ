# Testing Automations via API

This guide shows how to test automations directly via the API without using the UI.

## Overview

The Test button in the Ask AI interface calls a specific API endpoint that:
1. Generates YAML for the automation
2. Validates the YAML syntax and entities
3. Creates a temporary automation in Home Assistant with `[TEST]` prefix
4. Triggers the automation immediately so you can see it in action
5. Disables the automation after execution

## Prerequisites

- Services running: `ai-automation-service` on port 8024
- Home Assistant accessible and configured
- PowerShell (for the provided script)

## Quick Start

### Using the PowerShell Script

```powershell
# Test the automation from your image
.\scripts\test-automation-api.ps1 -Query "Every minute on the minute → Flash the living room lights in a warm white for 2 seconds, then switch to cool white for 2 seconds, repeating this for the duration."
```

### What Happens

1. **Query Creation**: The script creates a query with your automation description
2. **Suggestion Generation**: OpenAI generates automation suggestions
3. **Test Execution**: The first suggestion is tested by:
   - Generating YAML
   - Validating entities
   - Creating test automation in HA
   - Triggering it immediately
   - Disabling it to prevent repeat runs

### Example Output

```
🧪 Testing Automation via API
===============================
Query: Flash the living room lights...

📝 Step 1: Creating query...
✅ Query created with ID: abc123

📋 Step 2: Getting suggestions...
✅ Found 3 suggestions

🧪 Step 3: Testing first suggestion...
Testing suggestion: Create a rhythmic flash sequence...

✅ Test Results:
  Valid: True
  Executed: True
  Automation ID: automation.test_flash_sequence_xyz
  Message: ✅ Test automation executed successfully!
  
💡 Check your Home Assistant devices to see the automation in action!
   The test automation has been created with [TEST] prefix and is now disabled.
```

## Manual API Call

If you prefer to call the API directly:

### Step 1: Create Query

```powershell
$body = @{
    query = "Every minute on the minute → Flash the living room lights in a warm white for 2 seconds, then switch to cool white for 2 seconds, repeating this for the duration."
    user_id = "test_user"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8024/api/v1/ask-ai/query" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$queryId = $response.query_id
$suggestionId = $response.suggestions[0].suggestion_id
```

### Step 2: Test the Suggestion

```powershell
Invoke-RestMethod -Uri "http://localhost:8024/api/v1/ask-ai/query/$queryId/suggestions/$suggestionId/test" `
    -Method POST `
    -ContentType "application/json"
```

## API Response

The test endpoint returns:

```json
{
  "suggestion_id": "sugg-abc123",
  "query_id": "query-xyz789",
  "valid": true,
  "executed": true,
  "automation_id": "automation.test_flash_sequence_abc123",
  "automation_yaml": "...",  // Original YAML
  "test_automation_yaml": "...",  // YAML with [TEST] prefix
  "validation_details": {
    "error": null,
    "warnings": [],
    "entity_count": 1
  },
  "message": "✅ Test automation executed successfully! Check your Home Assistant devices. The test automation 'automation.test_flash_sequence_abc123' has been created and disabled."
}
```

## What to Expect

### Success Case

- **Valid**: `true` - YAML is syntactically correct
- **Executed**: `true` - Automation ran successfully
- **Message**: Success message with automation ID
- **Your Devices**: Should respond immediately (lights flash, switches toggle, etc.)

### Validation Warnings

If there are warnings:
- The automation may still execute
- Check the warnings to understand potential issues
- Common warnings:
  - Entity not found but similar entity exists
  - Service call may not work as expected

### Validation Errors

If validation fails:
- **Valid**: `false`
- **Executed**: `false`
- **Error**: Description of what's wrong
- Common errors:
  - Missing required YAML fields
  - Invalid entity ID
  - Syntax errors in generated YAML

## Viewing Test Automations in Home Assistant

After running a test, you can see the automation in Home Assistant:

1. Open Home Assistant UI
2. Go to **Settings** → **Automations & Scenes** → **Automations**
3. Look for automations with `[TEST]` prefix
4. These automations are **disabled** to prevent repeat execution
5. You can manually enable/delete them as needed

## Cleanup

Test automations accumulate in Home Assistant. To clean them up:

1. In Home Assistant, go to Automations
2. Filter or search for `[TEST]`
3. Select multiple test automations
4. Delete them in bulk

Alternatively, you can clean up via the Home Assistant API:

```powershell
# List all test automations
Invoke-RestMethod -Uri "http://YOUR_HA_IP:8123/api/states" `
    -Headers @{"Authorization"="Bearer YOUR_HA_TOKEN"} |
    Where-Object {$_.entity_id -like "automation.test_*"} |
    Select-Object entity_id, state

# Delete a specific test automation
Invoke-RestMethod -Uri "http://YOUR_HA_IP:8123/api/config/automation/config/automation.test_YOUR_ID" `
    -Method DELETE `
    -Headers @{"Authorization"="Bearer YOUR_HA_TOKEN"}
```

## Troubleshooting

### "Home Assistant client not initialized"

- Check that Home Assistant is running
- Verify the `HA_URL` and `HA_TOKEN` environment variables are set
- Check service logs: `docker-compose logs ai-automation-service`

### "Query not found" or "Suggestion not found"

- The query/suggestion may have expired or been deleted
- Try creating a new query
- Check the database if needed

### Automation doesn't trigger

- Check Home Assistant logs for errors
- Verify the automation was created: `States` page in HA
- Try manually triggering the automation from HA UI
- Check that devices/entities exist and are reachable

### YAML validation fails

- The generated YAML may have syntax errors
- Check the error message for details
- Try refining the query to be more specific
- Some complex automations may require manual YAML editing

## Advanced Usage

### Testing with Custom Parameters

```powershell
# Custom user ID
.\scripts\test-automation-api.ps1 -Query "Your query here" -UserId "my_test_user"

# Different base URL (e.g., production)
.\scripts\test-automation-api.ps1 -Query "Your query here" -BaseUrl "http://production:8024/api/v1/ask-ai"
```

### Testing Multiple Suggestions

Modify the script to test all suggestions, not just the first:

```powershell
# Test all suggestions
foreach ($suggestion in $suggestions) {
    Write-Host "Testing: $($suggestion.description)"
    # ... test logic here
}
```

### Running from curl (Linux/Mac)

```bash
#!/bin/bash

# Create query
QUERY="Your automation query here"
RESPONSE=$(curl -s -X POST http://localhost:8024/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"$QUERY\",\"user_id\":\"api_test\"}")

# Extract IDs
QUERY_ID=$(echo $RESPONSE | jq -r '.query_id')
SUGGESTION_ID=$(echo $RESPONSE | jq -r '.suggestions[0].suggestion_id')

# Test suggestion
curl -X POST "http://localhost:8024/api/v1/ask-ai/query/$QUERY_ID/suggestions/$SUGGESTION_ID/test" \
  -H "Content-Type: application/json"
```

## See Also

- [Ask AI Documentation](API_DOCUMENTATION_AI_AUTOMATION.md)
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Automation YAML Reference](https://www.home-assistant.io/docs/automation/)
