# OpenAI Prompt Structure for Automation Suggestions

This document explains the structure of prompts sent to OpenAI for generating automation suggestions, based on the code in `unified_prompt_builder.py`.

## Prompt Components

### 1. System Prompt
The system prompt is defined in `UNIFIED_SYSTEM_PROMPT` and includes:
- Role definition: "HIGHLY CREATIVE and experienced Home Assistant automation expert"
- Expertise areas: device capabilities, safety, best practices
- **CRITICAL**: Instructions to use EXACT devices/locations from clarification answers
- Advanced capability examples (numeric, enum, composite, binary)
- Guidelines for device naming, health scores, and automation creation

### 2. User Prompt Structure

The user prompt is built by `build_query_prompt()` and contains several sections:

#### A. Query Display
- The original user query (or enriched query if clarifications were provided)
- Format: `Based on this query: "{query_display}"`

#### B. Available Devices and Capabilities
- List of detected entities with:
  - Device name (friendly_name)
  - Manufacturer and model (if available)
  - Capabilities with detailed descriptions
  - Health scores with status
  - Area information

#### C. Enriched Entity Context (JSON)
- Complete entity information as JSON
- Includes:
  - Entity IDs
  - Friendly names
  - Areas
  - Capabilities
  - Device metadata
- Used to distinguish between group entities and individual entities

#### D. Clarification Context (CRITICAL - If Q&A Provided)
This section is added when the user has answered clarification questions:

```
═══════════════════════════════════════════════════════════════════════════════
CLARIFICATION CONTEXT (CRITICAL - USER PROVIDED ANSWERS):
═══════════════════════════════════════════════════════════════════════════════
The user was asked clarifying questions and provided these specific answers. 
YOU MUST USE THESE ANSWERS when generating suggestions. DO NOT IGNORE THEM.

1. Q: [Question]
   A: [Answer]
   Selected entities: [Entity IDs if provided]

CRITICAL REQUIREMENTS (MUST FOLLOW):
- Use the EXACT devices/locations mentioned in the answers above
- If the user specified specific devices, use ONLY those devices (e.g., "all four lights in office")
- If the user selected specific entities, use ONLY those entities from the enriched context
- Respect the user's choices - do NOT use different devices than what they specified
- If the user said "all four lights in office", find ALL FOUR lights from the office area
- If the user selected specific entities, prioritize those exact entities over generic device names
- The clarification answers OVERRIDE any assumptions you might make from the original query
```

#### E. Capability-Specific Automation Ideas
- Examples based on detected device capabilities
- Guidance on using numeric ranges, enum values, composite capabilities, etc.

#### F. Device Naming Requirements
**CRITICAL SECTION**:
```
CRITICAL: DEVICE NAMING REQUIREMENTS:
- ONLY use devices that are listed in the "Available devices and capabilities" section OR the "ENRICHED ENTITY CONTEXT" section above
- Count how many devices are actually available - DO NOT assume a specific number
- Use ACTUAL device friendly names from the enriched entity context JSON - DO NOT make up generic names like "Device 1" or "office lights"
- Reference devices by their EXACT friendly_name from the entities list
- If the enriched context shows 6 individual lights, list all 6 with their actual names
- DO NOT use group entity names unless the enriched context shows it's a group entity
- Example: If enriched context shows ["Office light 1", "Office light 2", "Office light 3"], use those exact names
```

#### G. Suggestion Generation Instructions
- Generate EXACTLY 2 suggestions
- Progression from CLOSE to ENHANCED CREATIVE
- JSON format requirements
- **CRITICAL**: For `devices_involved`, extract exact "friendly_name" values from enriched context

#### H. Final Warning (If Clarification Context Provided)
```
⚠️ IMPORTANT: If clarification context is provided:
- The user has already answered specific questions about their automation request
- Use the EXACT devices, locations, and preferences specified in the clarification answers
- If the user selected specific entities in Q&A, use ONLY those entities
- If the user specified "all four lights in office", find and list all four lights from the office area
- The clarification answers take PRECEDENCE over any assumptions from the original query
- DO NOT use different devices than what the user explicitly selected or confirmed in the Q&A
```

## How to Retrieve the Actual Prompt

### Method 1: Using the Script
```bash
# Get prompt for latest suggestion
python services/ai-automation-service/scripts/get_suggestion_prompt.py --latest

# Get prompt for specific query and suggestion
python services/ai-automation-service/scripts/get_suggestion_prompt.py <query_id> <suggestion_id>

# Search for queries by text
python services/ai-automation-service/scripts/get_suggestion_prompt.py --search "flash lights office"

# Save to file
python services/ai-automation-service/scripts/get_suggestion_prompt.py <query_id> <suggestion_id> --save
```

### Method 2: Direct Database Query
The prompts are stored in the `debug` object of each suggestion:
```python
query = await db.get(AskAIQueryModel, query_id)
suggestions = query.suggestions
for suggestion in suggestions:
    debug = suggestion.get('debug', {})
    system_prompt = debug.get('system_prompt')
    user_prompt = debug.get('user_prompt')
    filtered_prompt = debug.get('filtered_user_prompt')
    clarification_context = debug.get('clarification_context')
```

### Method 3: API Endpoint (Future Enhancement)
The `GET /query/{query_id}/suggestions` endpoint could be enhanced to return debug data.

## Common Issues

### Issue: Wrong Devices Selected
**Symptoms**: Suggestion mentions "all four lights in office" but only shows "Hue lightstrip outdoor 1"

**Possible Causes**:
1. **Enriched Entity Context Missing**: The enriched context JSON might not include all office lights
2. **Entity Mapping Issue**: The `devices_involved` from OpenAI might not match entities in enriched data
3. **Clarification Context Not Applied**: The clarification answers might not have been properly incorporated into the prompt
4. **Device Name Mismatch**: OpenAI might have used generic names instead of exact friendly_name values

**Debug Steps**:
1. Check `debug.clarification_context` - verify Q&A was included
2. Check `debug.entity_context_stats` - verify all office lights were in enriched context
3. Check `debug.openai_response` - see what devices OpenAI actually returned
4. Check `debug.device_selection` - see how devices were mapped to entities

### Issue: Confidence Mismatch
**Symptoms**: Overall confidence is 32% but suggestion confidence is 90%

**Explanation**:
- Overall confidence reflects the entire workflow (entity extraction, ambiguity resolution, etc.)
- Suggestion confidence reflects how well the specific automation matches the request
- These are calculated separately and serve different purposes

## Prompt Construction Flow

```
User Query
    ↓
Entity Extraction (with HA Conversation API)
    ↓
Clarification Questions (if ambiguities detected)
    ↓
User Answers + Selected Entities
    ↓
Rebuild Enriched Query (original + Q&A)
    ↓
Re-extract Entities (from enriched query)
    ↓
Re-enrich Entities (incorporate selected entities)
    ↓
Build Prompt:
  - System Prompt (UNIFIED_SYSTEM_PROMPT)
  - User Prompt:
    * Query Display (enriched)
    * Available Devices
    * Enriched Entity Context JSON
    * Clarification Context (if provided)
    * Capability Examples
    * Device Naming Requirements
    * Generation Instructions
    ↓
Send to OpenAI
    ↓
Parse Response
    ↓
Map Devices to Entities
    ↓
Store in Database (with debug data)
```

## Key Files

- **Prompt Building**: `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- **Query Processing**: `services/ai-automation-service/src/api/ask_ai_router.py`
- **Entity Enrichment**: `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- **Clarification**: `services/ai-automation-service/src/services/clarification/question_generator.py`

