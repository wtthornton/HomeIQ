# Custom Intent Research - Home Assistant Automation Creation

## Overview

**Goal:** Enable Home Assistant's Conversation API to accept natural language commands for creating automations, then route those to your `ai-automation-service`.

**Finding:** ✅ **This IS possible** using custom intents + intent_script + rest_command

---

## How Custom Intents Work

### Architecture Flow

```
User: "Create an automation to flash office lights for 10 seconds"
    ↓
HA Conversation API receives text
    ↓
Conversation Integration matches to custom intent
    ↓
Intent Script executes (calls your service)
    ↓
Your ai-automation-service receives request
    ↓
LLM generates YAML → Creates automation
    ↓
Response sent back to user
```

---

## Implementation Steps

### Step 1: Create Custom Sentences File

**Location:** `config/custom_sentences/en/automation_creation.yaml`

```yaml
language: "en"
intents:
  CreateFlashAutomation:
    data:
      - sentences:
          - "create an automation to flash {target} for {duration} seconds then restore"
          - "make an automation that flashes {target} for {duration} seconds and restores"
          - "set up an automation to flash {target} for {duration} seconds"
          - "create automation flash {target} {duration} seconds restore"
          - "new automation flash {target} {duration} seconds"
      slots:
        target:
          - name
          - area
        duration:
          - number
```

**Key Points:**
- `{target}` captures entity/area name (e.g., "office lights", "office")
- `{duration}` captures number (e.g., "10")
- Multiple sentence patterns increase match likelihood
- Optional words in `[]` don't need to match exactly

### Step 2: Create REST Command

**Location:** Add to `configuration.yaml`

```yaml
rest_command:
  create_automation_via_ai:
    url: "http://localhost:8007/api/v1/ask-ai/query"
    method: POST
    headers:
      Content-Type: "application/json"
      Authorization: "Bearer {{ YOUR_SERVICE_API_KEY }}"
    payload: |
      {
        "query": "Create an automation named '{{ automation_name }}' that flashes {{ target }} for {{ duration }} seconds and then restores its previous state. Enable it when done.",
        "suggestions_count": 1
      }
    content_type: "application/json"
```

**Alternative: More Direct Approach**

```yaml
rest_command:
  create_automation_via_ai:
    url: "http://localhost:8007/api/v1/ask-ai/query"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: |
      {
        "query": "{{ query_text }}",
        "suggestions_count": 1
      }
    content_type: "application/json"
    response_template: >
      {% if value.status_code == 200 %}
        {
          "success": true,
          "message": "Automation creation request sent"
        }
      {% else %}
        {
          "success": false,
          "error": "Failed to create automation"
        }
      {% endif %}
```

### Step 3: Create Intent Script

**Location:** Add to `configuration.yaml`

```yaml
intent_script:
  CreateFlashAutomation:
    action:
      # Option 1: Call REST command directly
      - service: rest_command.create_automation_via_ai
 sugsestions_count: 1
        data:
          automation_name: "Flash {{ target }} {{ duration }}s"
          target: "{{ target }}"
          duration: "{{ duration }}"
          query_text: "Create an automation named 'Flash {{ target }} {{ duration }}s' that flashes {{ target }} for {{ duration }} seconds and then restores its previous state. Enable it when done."
      # Option 2: Call Python script service (if you have one)
      # - service: python_script.create_flash_automation
      #   data:
      #     target: "{{ target }}"
      #     duration: "{{ duration }}"
    speech:
      text: >
        {% if target and duration %}
          I'll create an automation to flash {{ target }} for {{ duration }} seconds and restore it. This may take a few moments.
        {% else %}
          I need more information. Which lights should flash and for how long?
        {% endif %}
    slots:
      target:
        required: true
        description: "Target entity or area name"
      duration:
        required: true
        description: "Duration in seconds"
```

### Step 4: Enhanced Version with Entity Resolution

If you want to resolve friendly names to entity IDs before sending:

```yaml
intent_script:
  CreateFlashAutomation:
    action:
      - service: rest_command.create_automation_via_ai
        data_template:
          query_text: >
            {% set entity_id = none %}
            {% if 'light' in target.lower() %}
              {% set entity_id = states.light | selectattr('name', 'in', target) | map(attribute='entity_id') | list | first | default %}
            {% elif 'area' in target.lower() or target.lower() in states | map(attribute='attributes.area') | list | unique %}
              {% set area_lights = states.light | selectattr('attributes.area', 'in', target) | map(attribute='entity_id') | list | first | default %}
              {% set entity_id = area_lights %}
            {% endif %}
            {% if entity_id %}
              Create an automation named 'Flash {{ target }} {{ duration }}s' that flashes {{ entity_id }} for {{ duration }} seconds and then restores its previous state. Enable it when done.
            {% else %}
              Create an automation named 'Flash {{ target }} {{ duration }}s' that flashes {{ target }} for {{ duration }} seconds and then restores its previous state. Enable it when done.
            {% endif %}
    speech:
      text: >
        Creating automation for {{ target }} with {{ duration }} second flash duration.
```

---

## Complete Example Configuration

### File Structure

```
config/
├── configuration.yaml
├── custom_sentences/
│   └── en/
│       └── automation_creation.yaml
```

### configuration.yaml

```yaml
rest_command:
  create_automation_via_ai:
    url: "http://localhost:8007/api/v1/ask-ai/query"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: |
      {
        "query": "{{ query_text }}",
        "suggestions_count": 1
      }
    content_type: "application/json"

intent_script:
  CreateFlashAutomation:
    action:
      - service: rest_command.create_automation_via_ai
        data_template:
          query_text: >
            Create an automation named 'Flash {{ target }} {{ duration }}s' that flashes {{ target }} for {{ duration }} seconds and then restores its previous state. Enable it when done.
    speech:
      text: >
        I'll create that automation for you. It should be ready in a few seconds.
    slots:
      editorial_emphasis:
        description: "Target entity or area to flash"
        required: true
      duration:
        description: "Flash duration in seconds"
        required: true
```

### custom_sentences/en/automation_creation.yaml

```yaml
language: "en"
intents:
  CreateFlashAutomation:
    data:
      - sentences:
          - "create an automation to flash {target} for {duration} seconds then restore"
          - "make an automation that flashes {target} for {duration} seconds and restores"
          - "set up an automation to flash {target} for {duration} seconds"
          - "create automation flash {target} {duration} seconds restore"
          - "new automation flash {target} {duration} seconds"
      slots:
        target:
          - name
          - area
        duration:
          - number
```

---

## Advanced: Two-Step Process (More Reliable)

Since your ai-automation-service works with a query → suggestion → approve flow, you could make it a two-step conversation:

### Intent 1: Generate Suggestion

```yaml
# custom_sentences/en/automation_creation.yaml
language: "en"
intents:
  SuggestFlashAutomation:
    data:
      - sentences:
          - "suggest an automation to flash {target} for {duration} seconds"
          - "generate an automation idea for flashing {target} for {duration} seconds"
```

### Intent Script 1: Create Query + Get Suggestion

```yaml
intent_script:
  SuggestFlashAutomation:
    action:
      - service: rest_command.create_automation_query
        data_template:
          query_text: "Create an automation to flash {{ target }} for {{ duration }} seconds and restore previous state"
    speech:
      text: >
        I've created a suggestion for that automation. You can approve it in the Ask AI tab.
```

### Intent 2: Approve Suggestion

```yaml
# custom_sentences/en/automation_approval.yaml
language: "en"
intents:
  ApproveLastAutomation:
    data:
      - sentences:
          - "approve [the] [last] automation [suggestion]"
          - "yes create that automation"
          - "go ahead with that automation"
```

### Intent Script 2: Approve

```yaml
intent_script:
  ApproveLastAutomation:
    action:
      - service: rest_command.approve_automation_suggestion
        data:
          query_id: "{{ state_attr('sensor.last_automation_query_id', 'query_id') }}"
          suggestion_id: "{{ state_attr('sensor.last_automation_query_id', 'suggestion_id') }}"
    speech:
      text: "I've created and enabled that automation for you."
```

---

## Testing Your Custom Intent

### 1. Reload Conversation Integration

```yaml
# Developer Tools → Services
service: conversation.reload
```

### 2. Test via Developer Tools

```yaml
# Developer Tools → Conversation
Text: "create an automation to flash office lights for 10 seconds then restore"
```

### 3. Test via Voice/Alexa/Google

Just say: "Create an automation to flash office lights for 10 seconds then restore"

---

## Limitations & Considerations

### ❌ Limitations

1. **Slot Extraction:** HA's NLU may not perfectly extract `{target}` - it might capture "office lights" as two words vs one entity
2. **Complex Queries:** Very complex automation requests may not fit well into slots
3. **Error Handling:** Need robust error handling if your service is down
4. **Async Response:** Your service is async (LLM takes time) - user won't get immediate confirmation

### ✅ Benefits

1. **Simple Integration:** Works with existing Conversation API
2. **Voice Support:** Works with any voice assistant connected to HA
3. **No Code Changes:** All configuration-based
4. **Native HA Feel:** Feels like built-in HA functionality

---

## Recommended Approach for Your Use Case

### Option A: Simple Single-Step (Best for Testing)

Use the single-step intent that calls your service directly. Quick to test, but user gets async response.

### Option B: Two-Step (Best for Production)

1. **Step 1:** "Create an automation to flash office lights for 10 seconds"
   - Calls your service → Creates query + suggestion alerts, moderate reliability
   
2. **Step 2:** "Approve it" / "Yes, create it"
   - User approves → Automation is created
   - Better UX, allows review before creation

### Option C: Hybrid with HA Script

Create a HA script/automation that:
1. Receives the intent
2. Calls your ai-automation-service
3. Waits for response
4. Auto-approves if confidence is high (>0.9)
5. Notifies user of result

This gives you the simplicity of single-step with the reliability of two-step.

---

## Next Steps

1. ✅ Create `custom_sentences/en/automation_creation.yaml`
2. ✅ Add `rest_command` to `configuration.yaml`
3. ✅ Add `intent_script` to `configuration.yaml`
4. ✅ Reload conversation integration
5. ✅ Test via Developer Tools → Conversation
6. ✅ Test via voice assistant
7. ✅ Refine sentence patterns based on match results
8. ✅ Add error handling and user feedback

---

## References

- [Home Assistant Intent Scripts](https://www.home-assistant.io/integrations/intent_script/)
- [Home Assistant Custom Sentences](https://www.home-assistant.io/integrations/conversation/)
- [Home Assistant REST Command](https://www.home-assistant.io/integrations/rest_command/)
- [Rob Weber's Custom Intents Guide](https://robweber.github.io/smarthome/home_assistant_custom_intents/)

